/* Device HAL backend — only TU allowlisted for device headers.
 * Waveshare ESP32-S3-Touch-AMOLED-1.75: GPIO2 is SD MMC CLK — do not use as LED.
 */
#include "hal_board.h"

#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static void set_led(gcu_hal_t *self, int on) {
  (void)self;
  (void)on;
  /* No free status LED on this SKU without fighting SD/peripherals. */
}

static void delay_ms(gcu_hal_t *self, int ms) {
  (void)self;
  vTaskDelay(pdMS_TO_TICKS(ms > 0 ? ms : 1));
}

static int64_t now_ms(gcu_hal_t *self) {
  (void)self;
  /* esp_timer_get_time() is int64_t µs since boot; keep the division in
   * 64-bit. Do NOT narrow to long/int (32-bit here — wraps at ~24.8 days). */
  return esp_timer_get_time() / 1000;
}

static gcu_hal_t board_hal = {
    .set_led = set_led,
    .delay_ms = delay_ms,
    .now_ms = now_ms,
};

gcu_hal_t *gcu_make_board_hal(void) { return &board_hal; }
