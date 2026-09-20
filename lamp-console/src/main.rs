use std::{net::SocketAddr, sync::Arc, time::Duration};

use axum::{
    Json, Router,
    http::StatusCode,
    response::{Html, IntoResponse},
    routing::{get, post},
};
use rustuya::{Device, DeviceBuilder, Version};
use serde::{Deserialize, Serialize};

struct AppState {
    device: Device,
}

fn load_env() {
    if let Ok(p) = std::env::var("SMARTHOME_ENV") {
        let _ = dotenvy::from_path(p);
        return;
    }
    let _ = dotenvy::dotenv();
    let _ = dotenvy::from_path("../.env");
    if let Ok(exe) = std::env::current_exe() {
        for parent in [exe.parent(), exe.parent().and_then(|p| p.parent())] {
            if let Some(dir) = parent {
                let _ = dotenvy::from_path(dir.join(".env"));
                let _ = dotenvy::from_path(dir.join("../.env"));
            }
        }
    }
}

fn tuya_version() -> Version {
    match std::env::var("TUYA_LOCAL_VERSION").as_deref() {
        Ok("3.1") => Version::V3_1,
        Ok("3.2") => Version::V3_2,
        Ok("3.3") => Version::V3_3,
        Ok("3.4") => Version::V3_4,
        _ => Version::V3_5,
    }
}

fn device_from_env() -> Device {
    let id = std::env::var("TUYA_DEVICE_ID").expect("Нет TUYA_DEVICE_ID в .env");
    let key = std::env::var("TUYA_LOCAL_KEY").expect("Нет TUYA_LOCAL_KEY в .env");
    let ip = std::env::var("TUYA_LOCAL_IP").expect("Нет TUYA_LOCAL_IP в .env");
    DeviceBuilder::new(id, key)
        .address(ip)
        .version(tuya_version())
        .timeout(Duration::from_secs(5))
        .build()
}

#[derive(Serialize)]
struct ApiError {
    error: String,
}

async fn tuya_call(
    f: impl std::future::Future<Output = Result<Option<String>, rustuya::TuyaError>>,
) -> Result<serde_json::Value, (StatusCode, Json<ApiError>)> {
    match f.await {
        Ok(opt) => {
            let raw = opt.unwrap_or_else(|| "{}".to_string());
            let v: serde_json::Value =
                serde_json::from_str(&raw).unwrap_or(serde_json::json!({"raw": raw}));
            Ok(v)
        }
        Err(e) => Err((
            StatusCode::BAD_GATEWAY,
            Json(ApiError {
                error: format!("Tuya: {e}"),
            }),
        )),
    }
}

async fn api_status(
    axum::extract::State(st): axum::extract::State<Arc<AppState>>,
) -> impl IntoResponse {
    match tuya_call(st.device.status()).await {
        Ok(v) => (StatusCode::OK, Json(v)).into_response(),
        Err(e) => e.into_response(),
    }
}

#[derive(Deserialize)]
struct PowerReq {
    on: bool,
}

async fn api_power(
    axum::extract::State(st): axum::extract::State<Arc<AppState>>,
    Json(req): Json<PowerReq>,
) -> impl IntoResponse {
    match tuya_call(st.device.set_value(20, req.on)).await {
        Ok(v) => (StatusCode::OK, Json(v)).into_response(),
        Err(e) => e.into_response(),
    }
}

#[derive(Deserialize)]
struct ValueReq {
    value: i32,
}

fn clamp(v: i32, lo: i32, hi: i32) -> i32 {
    v.clamp(lo, hi)
}

async fn api_bright(
    axum::extract::State(st): axum::extract::State<Arc<AppState>>,
    Json(req): Json<ValueReq>,
) -> impl IntoResponse {
    let v = clamp(req.value, 10, 1000);
    let _ = st.device.set_value(20, true).await;
    if let Ok(Some(raw)) = st.device.status().await {
        if let Ok(val) = serde_json::from_str::<serde_json::Value>(&raw) {
            let mode = val
                .pointer("/dps/21")
                .and_then(|m| m.as_str())
                .unwrap_or("white");
            if mode == "colour" {
                let cur_h = val
                    .pointer("/dps/24")
                    .and_then(|s| s.as_str())
                    .and_then(|hex| u16::from_str_radix(hex.get(0..4)?, 16).ok())
                    .map(|h| h.min(360) as i32)
                    .unwrap_or(0);
                let _ = st.device.set_value(21, "colour").await;
                return match tuya_call(st.device.set_value(24, hsv_hex(cur_h, 1000, v))).await
                {
                    Ok(r) => (StatusCode::OK, Json(r)).into_response(),
                    Err(e) => e.into_response(),
                };
            }
        }
    }
    match tuya_call(st.device.set_value(22, v)).await {
        Ok(r) => (StatusCode::OK, Json(r)).into_response(),
        Err(e) => e.into_response(),
    }
}

async fn api_temp(
    axum::extract::State(st): axum::extract::State<Arc<AppState>>,
    Json(req): Json<ValueReq>,
) -> impl IntoResponse {
    let v = clamp(req.value, 0, 1000);
    let _ = st.device.set_value(20, true).await;
    let _ = st.device.set_value(21, "white").await;
    match tuya_call(st.device.set_value(23, v)).await {
        Ok(r) => (StatusCode::OK, Json(r)).into_response(),
        Err(e) => e.into_response(),
    }
}

#[derive(Deserialize)]
struct ModeReq {
    mode: String,
}

async fn api_mode(
    axum::extract::State(st): axum::extract::State<Arc<AppState>>,
    Json(req): Json<ModeReq>,
) -> impl IntoResponse {
    let mode = if req.mode == "colour" { "colour" } else { "white" };
    let _ = st.device.set_value(20, true).await;
    match tuya_call(st.device.set_value(21, mode)).await {
        Ok(r) => (StatusCode::OK, Json(r)).into_response(),
        Err(e) => e.into_response(),
    }
}

#[derive(Deserialize)]
struct ColorReq {
    h: i32,
    s: i32,
    v: i32,
}

fn hsv_hex(h: i32, s: i32, v: i32) -> String {
    format!("{:04x}{:04x}{:04x}", h.clamp(0, 360), s.clamp(0, 1000), v.clamp(0, 1000))
}

async fn api_color(
    axum::extract::State(st): axum::extract::State<Arc<AppState>>,
    Json(req): Json<ColorReq>,
) -> impl IntoResponse {
    let hex = hsv_hex(req.h, req.s, req.v);
    let _ = st.device.set_value(20, true).await;
    let _ = st.device.set_value(21, "colour").await;
    match tuya_call(st.device.set_value(24, hex.clone())).await {
        Ok(r) => (StatusCode::OK, Json(r)).into_response(),
        Err(e) => e.into_response(),
    }
}

async fn index() -> Html<&'static str> {
    Html(include_str!("../static/index.html"))
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();
    load_env();

    let device = device_from_env();
    tracing::info!(
        "lamp {} @ {} proto={}",
        device.id(),
        device.address(),
        device.version()
    );
    let state = Arc::new(AppState { device });

    let app = Router::new()
        .route("/", get(index))
        .route("/api/status", get(api_status))
        .route("/api/power", post(api_power))
        .route("/api/bright", post(api_bright))
        .route("/api/temp", post(api_temp))
        .route("/api/mode", post(api_mode))
        .route("/api/color", post(api_color))
        .with_state(state);

    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8080);
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    tracing::info!("console -> http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
