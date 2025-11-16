use axum::{
    extract::State,
    http::StatusCode,
    response::{Html, IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use base64::Engine;
use image::{ImageBuffer, ImageEncoder, Rgb, RgbImage};
use imageproc::drawing::draw_line_segment_mut;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use std::time::Duration;
use std::fs;
use std::path::Path;

const SCREEN_WIDTH: u32 = 240;
const SCREEN_HEIGHT: u32 = 135;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Config {
    address: String,
    lat: String,
    lon: String,
    username: String,
    password: String,
    interval: u64,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            address: String::new(),
            lat: String::new(),
            lon: String::new(),
            username: String::new(),
            password: String::new(),
            interval: 5,
        }
    }
}

impl Config {
    const CONFIG_FILE: &'static str = "pico-weather-config.json";

    /// Load configuration from file, or create default if not found
    fn load() -> Self {
        if Path::new(Self::CONFIG_FILE).exists() {
            match fs::read_to_string(Self::CONFIG_FILE) {
                Ok(data) => match serde_json::from_str(&data) {
                    Ok(config) => {
                        tracing::info!("Loaded configuration from {}", Self::CONFIG_FILE);
                        return config;
                    }
                    Err(e) => {
                        tracing::warn!("Failed to parse config file: {}", e);
                    }
                },
                Err(e) => {
                    tracing::warn!("Failed to read config file: {}", e);
                }
            }
        }

        tracing::info!("Using default configuration");
        Self::default()
    }

    /// Save configuration to file
    fn save(&self) -> Result<(), Box<dyn std::error::Error>> {
        let data = serde_json::to_string_pretty(self)?;
        fs::write(Self::CONFIG_FILE, data)?;
        tracing::info!("Saved configuration to {}", Self::CONFIG_FILE);
        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct WeatherData {
    temps: Vec<f32>,
    rains: Vec<f32>,
}

#[derive(Clone)]
struct AppState {
    config: Arc<RwLock<Config>>,
    weather: Arc<RwLock<Option<WeatherData>>>,
    last_image: Arc<RwLock<Option<Vec<u8>>>>,
    status: Arc<RwLock<String>>,
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    // Load saved configuration
    let config = Config::load();

    let state = AppState {
        config: Arc::new(RwLock::new(config)),
        weather: Arc::new(RwLock::new(None)),
        last_image: Arc::new(RwLock::new(None)),
        status: Arc::new(RwLock::new("Ready".to_string())),
    };

    // Start auto-update task
    let update_state = state.clone();
    tokio::spawn(async move {
        loop {
            let interval = {
                let config = update_state.config.read().await;
                config.interval
            };

            tokio::time::sleep(Duration::from_secs(interval * 60)).await;

            if let Err(e) = update_weather(update_state.clone()).await {
                tracing::error!("Auto-update failed: {}", e);
            }
        }
    });

    let app = Router::new()
        .route("/", get(index_handler))
        .route("/api/config", get(get_config).post(save_config))
        .route("/api/update", post(trigger_update))
        .route("/api/send", post(trigger_send))
        .route("/api/status", get(get_status))
        .route("/api/preview", get(get_preview))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:5710")
        .await
        .unwrap();

    tracing::info!("Server running on http://0.0.0.0:5710");

    axum::serve(listener, app).await.unwrap();
}

async fn index_handler() -> Html<&'static str> {
    Html(include_str!("index.html"))
}

async fn get_config(State(state): State<AppState>) -> Json<Config> {
    let config = state.config.read().await;
    Json(config.clone())
}

async fn save_config(
    State(state): State<AppState>,
    Json(config): Json<Config>,
) -> Result<StatusCode, (StatusCode, String)> {
    // Save to disk
    if let Err(e) = config.save() {
        return Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Failed to save config: {}", e),
        ));
    }

    // Update in-memory config
    let mut cfg = state.config.write().await;
    *cfg = config;

    Ok(StatusCode::OK)
}

async fn get_status(State(state): State<AppState>) -> Json<String> {
    let status = state.status.read().await;
    Json(status.clone())
}

async fn get_preview(State(state): State<AppState>) -> Response {
    let image_data = state.last_image.read().await;

    if let Some(data) = image_data.as_ref() {
        let base64_data = base64::engine::general_purpose::STANDARD.encode(data);
        Json(serde_json::json!({ "image": base64_data })).into_response()
    } else {
        (StatusCode::NOT_FOUND, "No image available").into_response()
    }
}

async fn trigger_update(State(state): State<AppState>) -> Result<Json<String>, (StatusCode, String)> {
    update_weather(state).await
        .map(|msg| Json(msg))
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e))
}

async fn trigger_send(State(state): State<AppState>) -> Result<Json<String>, (StatusCode, String)> {
    send_to_display(state).await
        .map(|msg| Json(msg))
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e))
}

async fn update_weather(state: AppState) -> Result<String, String> {
    *state.status.write().await = "Fetching weather data...".to_string();

    let config = state.config.read().await.clone();

    if config.username.is_empty() || config.password.is_empty() {
        let msg = "Username/password not configured".to_string();
        *state.status.write().await = msg.clone();
        return Err(msg);
    }

    if config.lat.is_empty() || config.lon.is_empty() {
        let msg = "Latitude/longitude not configured".to_string();
        *state.status.write().await = msg.clone();
        return Err(msg);
    }

    // Fetch weather data from Meteomatics API
    let url = format!(
        "https://api.meteomatics.com/now-1H--now+12H:PT5M/t_2m:F,precip_1h:mm/{},{}/json",
        config.lat, config.lon
    );

    let client = reqwest::Client::new();
    let auth = format!("{}:{}", config.username, config.password);
    let auth_header = format!("Basic {}", base64::engine::general_purpose::STANDARD.encode(auth.as_bytes()));

    let response = client
        .get(&url)
        .header("Authorization", auth_header)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !response.status().is_success() {
        let msg = format!("API error: {}", response.status());
        *state.status.write().await = msg.clone();
        return Err(msg);
    }

    let json: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("JSON parse error: {}", e))?;

    // Parse weather data
    let (temps, rains) = parse_weather_json(&json)
        .map_err(|e| format!("Parse error: {}", e))?;

    if temps.is_empty() {
        let msg = "No temperature data received".to_string();
        *state.status.write().await = msg.clone();
        return Err(msg);
    }

    *state.weather.write().await = Some(WeatherData { temps, rains });
    *state.status.write().await = "Weather data updated".to_string();

    // Render and send
    render_weather(state.clone()).await?;
    send_to_display(state).await
}

fn parse_weather_json(json: &serde_json::Value) -> Result<(Vec<f32>, Vec<f32>), String> {
    let mut temps = Vec::new();
    let mut rains = Vec::new();

    let data = json.get("data")
        .and_then(|d| d.as_array())
        .ok_or("No data array")?;

    for param in data {
        let param_name = param.get("parameter")
            .and_then(|p| p.as_str())
            .ok_or("No parameter name")?;

        let coords = param.get("coordinates")
            .and_then(|c| c.as_array())
            .ok_or("No coordinates")?;

        if coords.is_empty() {
            continue;
        }

        let dates = coords[0].get("dates")
            .and_then(|d| d.as_array())
            .ok_or("No dates")?;

        for date in dates {
            let value = date.get("value")
                .and_then(|v| v.as_f64())
                .ok_or("No value")? as f32;

            if param_name == "t_2m:F" {
                temps.push(value);
            } else if param_name == "precip_1h:mm" {
                rains.push(value);
            }
        }
    }

    Ok((temps, rains))
}

async fn render_weather(state: AppState) -> Result<(), String> {
    *state.status.write().await = "Rendering image...".to_string();

    let weather = state.weather.read().await;
    let weather_data = weather.as_ref().ok_or("No weather data")?;

    if weather_data.temps.is_empty() {
        return Err("No temperature data".to_string());
    }

    // Use shared rendering function
    let img = render_weather_image(weather_data);

    // Store as PNG for preview
    let mut png_data = Vec::new();
    {
        let encoder = image::codecs::png::PngEncoder::new(&mut png_data);
        encoder
            .write_image(
                img.as_raw(),
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
                image::ExtendedColorType::Rgb8,
            )
            .map_err(|e| format!("PNG encode error: {}", e))?;
    }

    *state.last_image.write().await = Some(png_data);
    *state.status.write().await = "Image rendered".to_string();

    Ok(())
}

/// Render weather data to an image
/// Returns RgbImage that can be encoded as PNG or RGB565
fn render_weather_image(weather_data: &WeatherData) -> RgbImage {
    let temps = &weather_data.temps;
    let rains = &weather_data.rains;

    let n = temps.len();
    let now_i = 13.min(n - 1); // 1 hour at 5 minute intervals

    // Calculate ranges
    let min_temp = temps.iter().cloned().fold(f32::INFINITY, f32::min);
    let max_temp = temps.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
    let max_rain = rains.iter().cloned().fold(0.0f32, f32::max).max(12.7);

    let mid_temp = (min_temp + max_temp) * 0.5;
    let temp_rng = (max_temp - min_temp).max(20.0);
    let min_temp_range = mid_temp - temp_rng * 0.5;

    // Create image
    let mut img: RgbImage = ImageBuffer::from_pixel(SCREEN_WIDTH, SCREEN_HEIGHT, Rgb([0, 0, 0]));

    // Draw "now" line (gray vertical line at current time)
    let xn = ((now_i * SCREEN_WIDTH as usize) / n) as i32;
    draw_line_segment_mut(
        &mut img,
        (xn as f32, (SCREEN_HEIGHT - 1) as f32),
        (xn as f32, 0.0),
        Rgb([128, 128, 128]),
    );

    // Draw rain bars (cyan)
    for (i, &rain) in rains.iter().enumerate().take(n) {
        if rain > 0.0 {
            let x0 = (i * SCREEN_WIDTH as usize) / n;
            let x1 = ((i + 1) * SCREEN_WIDTH as usize) / n;
            let y_rain = ((SCREEN_HEIGHT as f32 - 20.0) * rain / max_rain) as u32;

            for x in x0..x1 {
                for y in (SCREEN_HEIGHT - 1 - y_rain)..(SCREEN_HEIGHT - 20) {
                    if (x as u32) < SCREEN_WIDTH && (y as u32) < SCREEN_HEIGHT {
                        img.put_pixel(x as u32, y as u32, Rgb([0, 192, 255]));
                    }
                }
            }
        }
    }

    // Draw temperature line (orange)
    let mut last_x = 0;
    let mut last_y = (SCREEN_HEIGHT as f32 - 1.0
        - (SCREEN_HEIGHT as f32 * (temps[0] - min_temp_range) / temp_rng)) as i32;

    for (i, &temp) in temps.iter().enumerate().skip(1) {
        let x = ((i * SCREEN_WIDTH as usize) / n) as i32;
        let y = (SCREEN_HEIGHT as f32 - 1.0
            - (SCREEN_HEIGHT as f32 * (temp - min_temp_range) / temp_rng)) as i32;

        // Draw thick line (simulate 2px width)
        draw_line_segment_mut(
            &mut img,
            (last_x as f32, last_y as f32),
            (x as f32, y as f32),
            Rgb([255, 127, 0]),
        );
        draw_line_segment_mut(
            &mut img,
            (last_x as f32, (last_y + 1) as f32),
            (x as f32, (y + 1) as f32),
            Rgb([255, 127, 0]),
        );

        last_x = x;
        last_y = y;
    }

    img
}

fn convert_to_rgb565(img: &RgbImage) -> Vec<u8> {
    let (width, height) = img.dimensions();
    let mut data = Vec::with_capacity((width * height * 2) as usize);

    for y in 0..height {
        for x in 0..width {
            let pixel = img.get_pixel(x, y);
            let r = (pixel[0] >> 3) as u16;
            let g = (pixel[1] >> 2) as u16;
            let b = (pixel[2] >> 3) as u16;
            let rgb565 = (r << 11) | (g << 5) | b;

            // Little-endian
            data.push((rgb565 & 0xFF) as u8);
            data.push((rgb565 >> 8) as u8);
        }
    }

    data
}

async fn send_to_display(state: AppState) -> Result<String, String> {
    *state.status.write().await = "Sending to display...".to_string();

    let config = state.config.read().await.clone();

    if config.address.is_empty() {
        let msg = "Display address not configured".to_string();
        *state.status.write().await = msg.clone();
        return Err(msg);
    }

    let weather = state.weather.read().await;
    let weather_data = weather.as_ref().ok_or("No weather data")?;

    // Use shared rendering function
    let img = render_weather_image(weather_data);

    // Convert to RGB565 format
    let rgb565_data = convert_to_rgb565(&img);

    // Send to Pico W
    let url = format!("http://{}", config.address);

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| format!("Client build failed: {}", e))?;

    let response = client
        .put(&url)
        .header("Content-Type", "application/octet-stream")
        .header("Content-Length", rgb565_data.len())
        .body(rgb565_data)
        .send()
        .await
        .map_err(|e| format!("Send failed: {}", e))?;

    if response.status().is_success() {
        let msg = format!("Sent {} bytes to display", SCREEN_WIDTH * SCREEN_HEIGHT * 2);
        *state.status.write().await = msg.clone();
        Ok(msg)
    } else {
        let msg = format!("Display returned error: {}", response.status());
        *state.status.write().await = msg.clone();
        Err(msg)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Test RGB565 conversion for pure red
    #[test]
    fn test_rgb565_red() {
        let mut img = RgbImage::new(1, 1);
        img.put_pixel(0, 0, Rgb([255, 0, 0])); // Pure red

        let rgb565 = convert_to_rgb565(&img);

        assert_eq!(rgb565.len(), 2, "RGB565 should be 2 bytes");
        // Red: 11111 000000 00000 = 0xF800
        // Little-endian: low byte first
        assert_eq!(rgb565[0], 0x00); // Low byte
        assert_eq!(rgb565[1], 0xF8); // High byte
    }

    /// Test RGB565 conversion for pure green
    #[test]
    fn test_rgb565_green() {
        let mut img = RgbImage::new(1, 1);
        img.put_pixel(0, 0, Rgb([0, 255, 0])); // Pure green

        let rgb565 = convert_to_rgb565(&img);

        assert_eq!(rgb565.len(), 2);
        // Green: 00000 111111 00000 = 0x07E0
        assert_eq!(rgb565[0], 0xE0); // Low byte
        assert_eq!(rgb565[1], 0x07); // High byte
    }

    /// Test RGB565 conversion for pure blue
    #[test]
    fn test_rgb565_blue() {
        let mut img = RgbImage::new(1, 1);
        img.put_pixel(0, 0, Rgb([0, 0, 255])); // Pure blue

        let rgb565 = convert_to_rgb565(&img);

        assert_eq!(rgb565.len(), 2);
        // Blue: 00000 000000 11111 = 0x001F
        assert_eq!(rgb565[0], 0x1F); // Low byte
        assert_eq!(rgb565[1], 0x00); // High byte
    }

    /// Test RGB565 conversion for white
    #[test]
    fn test_rgb565_white() {
        let mut img = RgbImage::new(1, 1);
        img.put_pixel(0, 0, Rgb([255, 255, 255])); // Pure white

        let rgb565 = convert_to_rgb565(&img);

        assert_eq!(rgb565.len(), 2);
        // White: 11111 111111 11111 = 0xFFFF
        assert_eq!(rgb565[0], 0xFF); // Low byte
        assert_eq!(rgb565[1], 0xFF); // High byte
    }

    /// Test RGB565 conversion for black
    #[test]
    fn test_rgb565_black() {
        let mut img = RgbImage::new(1, 1);
        img.put_pixel(0, 0, Rgb([0, 0, 0])); // Pure black

        let rgb565 = convert_to_rgb565(&img);

        assert_eq!(rgb565.len(), 2);
        // Black: 00000 000000 00000 = 0x0000
        assert_eq!(rgb565[0], 0x00); // Low byte
        assert_eq!(rgb565[1], 0x00); // High byte
    }

    /// Test RGB565 conversion for orange (temperature line color)
    #[test]
    fn test_rgb565_orange() {
        let mut img = RgbImage::new(1, 1);
        img.put_pixel(0, 0, Rgb([255, 127, 0])); // Orange

        let rgb565 = convert_to_rgb565(&img);

        assert_eq!(rgb565.len(), 2);
        // RGB888 to RGB565:
        // R: 255 >> 3 = 31 (0x1F)
        // G: 127 >> 2 = 31 (0x1F)
        // B:   0 >> 3 =  0 (0x00)
        // RGB565: 11111 011111 00000 = 0xFBE0
        assert_eq!(rgb565[0], 0xE0); // Low byte
        assert_eq!(rgb565[1], 0xFB); // High byte
    }

    /// Test RGB565 buffer size for full screen
    #[test]
    fn test_rgb565_buffer_size() {
        let img = RgbImage::new(SCREEN_WIDTH, SCREEN_HEIGHT);
        let rgb565 = convert_to_rgb565(&img);

        let expected_size = (SCREEN_WIDTH * SCREEN_HEIGHT * 2) as usize;
        assert_eq!(
            rgb565.len(),
            expected_size,
            "Buffer size should be width * height * 2 bytes"
        );
    }

    /// Test that RGB565 conversion is deterministic
    #[test]
    fn test_rgb565_deterministic() {
        let mut img = RgbImage::new(10, 10);
        for y in 0..10 {
            for x in 0..10 {
                img.put_pixel(x, y, Rgb([123, 45, 67]));
            }
        }

        let data1 = convert_to_rgb565(&img);
        let data2 = convert_to_rgb565(&img);

        assert_eq!(data1, data2, "Conversion should be deterministic");
    }
}
