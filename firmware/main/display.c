/* Device display port — Waveshare ESP32-S3-Touch-LCD-4.3B / 4.3B-BOX.
 * RGB 800×480 panel + CH422G I2C expander (backlight EXIO2, LCD RST EXIO3).
 * Only this TU (plus hal_board) may include freertos / esp_* / driver headers.
 *
 * Pin map / timings from Waveshare ESP32-S3-Touch-LCD-4.3B official demo
 * (github.com/waveshareteam/ESP32-S3-Touch-LCD-4.3B).
 */
#include "display.h"

#include "driver/gpio.h"
#include "driver/i2c.h"
#include "esp_heap_caps.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_panel_rgb.h"
#include "esp_lcd_touch.h"
#include "esp_lcd_touch_gt911.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lvgl.h"

#include <string.h>

/* ---- I2C (CH422G expander @ 0x24/0x38, shared with GT911 touch) ---- */
#define I2C_MASTER_NUM I2C_NUM_0
#define I2C_MASTER_SDA_IO 8
#define I2C_MASTER_SCL_IO 9
#define I2C_MASTER_FREQ_HZ 400000
#define I2C_MASTER_TIMEOUT_MS 1000
#define CH422G_ADDR_CFG 0x24
#define CH422G_ADDR_OUT 0x38

#define TP_INT_GPIO GPIO_NUM_4

/* ---- RGB panel pins (Waveshare 4.3B) ---- */
#define LCD_H_RES 800
#define LCD_V_RES 480
#define LCD_PCLK_HZ (16 * 1000 * 1000)
#define LCD_BOUNCE_LINES 10

#define LCD_PIN_VSYNC GPIO_NUM_3
#define LCD_PIN_HSYNC GPIO_NUM_46
#define LCD_PIN_DE GPIO_NUM_5
#define LCD_PIN_PCLK GPIO_NUM_7
/* B0..B4, G0..G5, R0..R4 */
#define LCD_PIN_DATA0 GPIO_NUM_14
#define LCD_PIN_DATA1 GPIO_NUM_38
#define LCD_PIN_DATA2 GPIO_NUM_18
#define LCD_PIN_DATA3 GPIO_NUM_17
#define LCD_PIN_DATA4 GPIO_NUM_10
#define LCD_PIN_DATA5 GPIO_NUM_39
#define LCD_PIN_DATA6 GPIO_NUM_0
#define LCD_PIN_DATA7 GPIO_NUM_45
#define LCD_PIN_DATA8 GPIO_NUM_48
#define LCD_PIN_DATA9 GPIO_NUM_47
#define LCD_PIN_DATA10 GPIO_NUM_21
#define LCD_PIN_DATA11 GPIO_NUM_1
#define LCD_PIN_DATA12 GPIO_NUM_2
#define LCD_PIN_DATA13 GPIO_NUM_42
#define LCD_PIN_DATA14 GPIO_NUM_41
#define LCD_PIN_DATA15 GPIO_NUM_40

static const char *TAG = "display";

static esp_lcd_panel_handle_t s_panel;
static uint16_t *s_face;
static lv_display_t *s_lv_disp;
static lv_indev_t *s_lv_touch;
static esp_lcd_touch_handle_t s_touch;
static int s_i2c_ready;

static esp_err_t i2c_init(void) {
  if (s_i2c_ready) {
    return ESP_OK;
  }
  i2c_config_t conf = {
      .mode = I2C_MODE_MASTER,
      .sda_io_num = I2C_MASTER_SDA_IO,
      .scl_io_num = I2C_MASTER_SCL_IO,
      .sda_pullup_en = GPIO_PULLUP_ENABLE,
      .scl_pullup_en = GPIO_PULLUP_ENABLE,
      .master.clk_speed = I2C_MASTER_FREQ_HZ,
  };
  esp_err_t err = i2c_param_config(I2C_MASTER_NUM, &conf);
  if (err != ESP_OK) {
    return err;
  }
  err = i2c_driver_install(I2C_MASTER_NUM, conf.mode, 0, 0, 0);
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
    return err;
  }
  s_i2c_ready = 1;
  return ESP_OK;
}

static esp_err_t ch422g_write_out(uint8_t value) {
  return i2c_master_write_to_device(I2C_MASTER_NUM, CH422G_ADDR_OUT, &value, 1,
                                    pdMS_TO_TICKS(I2C_MASTER_TIMEOUT_MS));
}

static esp_err_t ch422g_enable_outputs(void) {
  uint8_t cfg = 0x01; /* Waveshare: put CH422G in output mode */
  return i2c_master_write_to_device(I2C_MASTER_NUM, CH422G_ADDR_CFG, &cfg, 1,
                                    pdMS_TO_TICKS(I2C_MASTER_TIMEOUT_MS));
}

/*
 * CH422G EXIO map (4.3B wiki):
 *   EXIO1 = TP_RST, EXIO2 = DISP (backlight), EXIO3 = LCD_RST (panel).
 */
static void touch_hw_reset(void) {
  /* Waveshare sequence: hold INT low (addr 0x5D), pulse TP_RST via CH422G. */
  gpio_config_t io = {
      .pin_bit_mask = 1ULL << TP_INT_GPIO,
      .mode = GPIO_MODE_OUTPUT,
      .pull_up_en = GPIO_PULLUP_DISABLE,
      .pull_down_en = GPIO_PULLDOWN_DISABLE,
      .intr_type = GPIO_INTR_DISABLE,
  };
  gpio_config(&io);
  gpio_set_level(TP_INT_GPIO, 0);
  vTaskDelay(pdMS_TO_TICKS(10));
  (void)ch422g_write_out(0x2C);
  vTaskDelay(pdMS_TO_TICKS(100));
  (void)ch422g_write_out(0x2E);
  vTaskDelay(pdMS_TO_TICKS(200));
  gpio_reset_pin(TP_INT_GPIO);
  (void)ch422g_write_out(0x1E);
  vTaskDelay(pdMS_TO_TICKS(50));
}

static bool touch_try_addr(uint8_t addr) {
  esp_lcd_panel_io_handle_t tp_io = NULL;
  esp_lcd_panel_io_i2c_config_t io_cfg = ESP_LCD_TOUCH_IO_I2C_GT911_CONFIG();
  io_cfg.dev_addr = addr;
  /* GT911 macro sets scl_speed_hz=100000, but legacy i2c_driver path
   * (esp_lcd_new_panel_io_i2c_v1) rejects any non-zero value. Bus rate is
   * already set by i2c_param_config (400 kHz). */
  io_cfg.scl_speed_hz = 0;
  esp_err_t err = esp_lcd_new_panel_io_i2c(
      (esp_lcd_i2c_bus_handle_t)I2C_MASTER_NUM, &io_cfg, &tp_io);
  if (err != ESP_OK) {
    ESP_LOGW(TAG, "touch panel_io 0x%02X: %s", addr, esp_err_to_name(err));
    return false;
  }

  /* Must outlive init — driver keeps driver_data pointer. */
  static esp_lcd_touch_io_gt911_config_t s_gt911_cfg;
  s_gt911_cfg.dev_addr = addr;
  const esp_lcd_touch_config_t tp_cfg = {
      .x_max = FACE_W,
      .y_max = FACE_H,
      .rst_gpio_num = GPIO_NUM_NC, /* RST via CH422G already done */
      .int_gpio_num = GPIO_NUM_NC, /* poll mode */
      .levels =
          {
              .reset = 0,
              .interrupt = 0,
          },
      .flags =
          {
              .swap_xy = 0,
              .mirror_x = 0,
              .mirror_y = 0,
          },
      .driver_data = &s_gt911_cfg,
  };
  err = esp_lcd_touch_new_i2c_gt911(tp_io, &tp_cfg, &s_touch);
  if (err != ESP_OK) {
    ESP_LOGW(TAG, "GT911 @0x%02X: %s", addr, esp_err_to_name(err));
    s_touch = NULL;
    (void)esp_lcd_panel_io_del(tp_io);
    return false;
  }
  ESP_LOGI(TAG, "GT911 touch driver ready @0x%02X", addr);
  return true;
}

static bool touch_driver_init(void) {
  if (!s_i2c_ready) {
    return false;
  }
  /* INT held low during reset → primary addr 0x5D; some boards land on 0x14. */
  if (touch_try_addr(ESP_LCD_TOUCH_IO_I2C_GT911_ADDRESS)) {
    return true;
  }
  if (touch_try_addr(ESP_LCD_TOUCH_IO_I2C_GT911_ADDRESS_BACKUP)) {
    return true;
  }
  ESP_LOGW(TAG, "GT911 not found (touch nav limited to serial)");
  return false;
}

static bool board_power_and_reset(void) {
  if (i2c_init() != ESP_OK) {
    ESP_LOGE(TAG, "I2C init failed (CH422G)");
    return false;
  }
  if (ch422g_enable_outputs() != ESP_OK) {
    ESP_LOGW(TAG, "CH422G enable failed — continuing (may already be on)");
  }

  /* LCD reset low, backlight off-ish */
  (void)ch422g_write_out(0x00);
  vTaskDelay(pdMS_TO_TICKS(20));
  /* Release LCD RST (EXIO3) + enable backlight (EXIO2) pattern 0x1E */
  (void)ch422g_write_out(0x1E);
  vTaskDelay(pdMS_TO_TICKS(100));
  ESP_LOGI(TAG, "CH422G: LCD RST + backlight asserted");
  touch_hw_reset();
  (void)touch_driver_init();
  return true;
}

static bool init_rgb_panel(void) {
  esp_lcd_rgb_panel_config_t panel_config = {
      .clk_src = LCD_CLK_SRC_DEFAULT,
      .timings =
          {
              .pclk_hz = LCD_PCLK_HZ,
              .h_res = LCD_H_RES,
              .v_res = LCD_V_RES,
              .hsync_pulse_width = 4,
              .hsync_back_porch = 8,
              .hsync_front_porch = 8,
              .vsync_pulse_width = 4,
              .vsync_back_porch = 8,
              .vsync_front_porch = 8,
              .flags =
                  {
                      .pclk_active_neg = 1,
                  },
          },
      .data_width = 16,
      .bits_per_pixel = 16,
      .num_fbs = 1,
      .bounce_buffer_size_px = LCD_H_RES * LCD_BOUNCE_LINES,
      .sram_trans_align = 4,
      .psram_trans_align = 64,
      .hsync_gpio_num = LCD_PIN_HSYNC,
      .vsync_gpio_num = LCD_PIN_VSYNC,
      .de_gpio_num = LCD_PIN_DE,
      .pclk_gpio_num = LCD_PIN_PCLK,
      .disp_gpio_num = -1,
      .data_gpio_nums =
          {
              LCD_PIN_DATA0,  LCD_PIN_DATA1,  LCD_PIN_DATA2,  LCD_PIN_DATA3,
              LCD_PIN_DATA4,  LCD_PIN_DATA5,  LCD_PIN_DATA6,  LCD_PIN_DATA7,
              LCD_PIN_DATA8,  LCD_PIN_DATA9,  LCD_PIN_DATA10, LCD_PIN_DATA11,
              LCD_PIN_DATA12, LCD_PIN_DATA13, LCD_PIN_DATA14, LCD_PIN_DATA15,
          },
      .flags =
          {
              .fb_in_psram = 1,
          },
  };

  esp_err_t err = esp_lcd_new_rgb_panel(&panel_config, &s_panel);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "esp_lcd_new_rgb_panel: %s", esp_err_to_name(err));
    return false;
  }
  err = esp_lcd_panel_init(s_panel);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "esp_lcd_panel_init: %s", esp_err_to_name(err));
    return false;
  }
  return true;
}

bool display_init(void) {
  const size_t face_bytes = (size_t)FACE_W * FACE_H * sizeof(uint16_t);

  if (!board_power_and_reset()) {
    ESP_LOGW(TAG, "expander sequence incomplete — trying panel anyway");
  }

  s_face = (uint16_t *)heap_caps_malloc(
      face_bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!s_face) {
    s_face = (uint16_t *)heap_caps_malloc(face_bytes, MALLOC_CAP_8BIT);
  }
  if (!s_face) {
    ESP_LOGE(TAG, "face buffer alloc failed (need PSRAM for 800x480 RGB565)");
    return false;
  }
  memset(s_face, 0, face_bytes);

  if (!init_rgb_panel()) {
    return false;
  }

  /* Re-assert backlight after panel clocks start. */
  (void)ch422g_write_out(0x1E);

  ESP_LOGI(TAG, "RGB 4.3B ready face %dx%d", FACE_W, FACE_H);
  return true;
}

uint16_t *display_face_buffer(void) { return s_face; }

void display_present(const uint16_t *face_rgb565) {
  if (!s_panel || !face_rgb565) {
    return;
  }
  /* Native RGB565 — no SPI byte-swap (unlike QSPI AMOLED path). */
  esp_lcd_panel_draw_bitmap(s_panel, 0, 0, FACE_W, FACE_H, face_rgb565);
}

/* ---- LVGL display driver ------------------------------------------------ */

static uint32_t aether_lv_tick_ms(void) {
  return (uint32_t)(esp_timer_get_time() / 1000ULL);
}

static void aether_lv_flush(lv_display_t *disp, const lv_area_t *area,
                            uint8_t *px_map) {
  (void)area;
  display_present((const uint16_t *)px_map);
  lv_display_flush_ready(disp);
}

bool display_lvgl_init(void) {
  if (!s_face || !s_panel) {
    ESP_LOGE(TAG, "display_lvgl_init: call display_init first");
    return false;
  }

  lv_init();
  lv_tick_set_cb(aether_lv_tick_ms);

  s_lv_disp = lv_display_create(FACE_W, FACE_H);
  if (!s_lv_disp) {
    ESP_LOGE(TAG, "lv_display_create failed");
    return false;
  }

  lv_display_set_color_format(s_lv_disp, LV_COLOR_FORMAT_RGB565);
  lv_display_set_flush_cb(s_lv_disp, aether_lv_flush);

  const size_t face_bytes = (size_t)FACE_W * FACE_H * sizeof(uint16_t);
  lv_display_set_buffers(s_lv_disp, s_face, NULL, face_bytes,
                         LV_DISPLAY_RENDER_MODE_FULL);

  ESP_LOGI(TAG, "LVGL display %dx%d RGB565 full-frame flush→RGB 4.3B", FACE_W,
           FACE_H);
  return true;
}

uint16_t *display_alloc_canvas(int w, int h) {
  if (w <= 0 || h <= 0) {
    return NULL;
  }
  const size_t n = (size_t)w * (size_t)h * sizeof(uint16_t);
  uint16_t *p =
      (uint16_t *)heap_caps_malloc(n, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!p) {
    p = (uint16_t *)heap_caps_malloc(n, MALLOC_CAP_8BIT);
  }
  if (p) {
    memset(p, 0, n);
  }
  return p;
}

/* Latest sample (debug / optional non-LVGL readers). LVGL reads in indev cb. */
static int s_touch_x;
static int s_touch_y;
static int s_touch_pr;

static void touch_sample(void) {
  if (!s_touch) {
    s_touch_pr = 0;
    return;
  }

  esp_lcd_touch_read_data(s_touch);
  uint16_t x[1] = {0}, y[1] = {0}, strength[1] = {0};
  uint8_t cnt = 0;
  bool ok = esp_lcd_touch_get_coordinates(s_touch, x, y, strength, &cnt, 1);
  if (ok && cnt > 0) {
    int tx = (int)x[0];
    int ty = (int)y[0];
    if (tx < 0) {
      tx = 0;
    }
    if (ty < 0) {
      ty = 0;
    }
    if (tx >= FACE_W) {
      tx = FACE_W - 1;
    }
    if (ty >= FACE_H) {
      ty = FACE_H - 1;
    }
    s_touch_x = tx;
    s_touch_y = ty;
    s_touch_pr = 1;
  } else {
    s_touch_pr = 0;
  }
}

void display_touch_poll(void) {
  /* Prefer sampling from the LVGL indev callback (one read per indev tick).
   * Kept for callers that want a sample outside LVGL. */
  touch_sample();
}

bool display_touch_get(int *x, int *y, int *pressed) {
  if (x) {
    *x = s_touch_x;
  }
  if (y) {
    *y = s_touch_y;
  }
  if (pressed) {
    *pressed = s_touch_pr;
  }
  return s_touch_pr != 0;
}

/* Indev only reports the last sample from display_touch_poll / touch_sample.
 * Sampling here as well would double-read GT911 and clear the status reg. */
static void lv_touch_read_cb(lv_indev_t *indev, lv_indev_data_t *data) {
  (void)indev;
  if (s_touch_pr) {
    data->point.x = s_touch_x;
    data->point.y = s_touch_y;
    data->state = LV_INDEV_STATE_PRESSED;
  } else {
    data->point.x = s_touch_x;
    data->point.y = s_touch_y;
    data->state = LV_INDEV_STATE_RELEASED;
  }
}

bool display_touch_lvgl_init(void) {
  if (!s_lv_disp) {
    return false;
  }
  s_lv_touch = lv_indev_create();
  if (!s_lv_touch) {
    return false;
  }
  lv_indev_set_type(s_lv_touch, LV_INDEV_TYPE_POINTER);
  lv_indev_set_read_cb(s_lv_touch, lv_touch_read_cb);
  lv_indev_set_display(s_lv_touch, s_lv_disp);
  /* Default scroll_limit is 10px — finger jitter on capacitive glass often
   * exceeds that and steals CLICKED from buttons inside scrollables. 24 is
   * still a short swipe start for tileview. */
  lv_indev_set_scroll_limit(s_lv_touch, 24);
  lv_indev_set_long_press_time(s_lv_touch, 400);
  ESP_LOGI(TAG, "LVGL touch indev registered (GT911 %s)",
           s_touch ? "ok" : "missing");
  return true;
}
