#ifndef AETHER_WIFI_STA_H
#define AETHER_WIFI_STA_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Thin station wrapper over ESP-IDF esp_wifi + esp_netif + nvs_flash.
 * No bespoke radio stack — same path as IDF wifi/getting_started/station.
 * API prefix aether_wifi_* avoids clashing with IDF internal symbols
 * (e.g. wifi_sta_disconnect).
 */

typedef enum {
  AETHER_WIFI_OFF = 0,
  AETHER_WIFI_STARTING,
  AETHER_WIFI_DISCONNECTED,
  AETHER_WIFI_SCANNING,
  AETHER_WIFI_CONNECTING,
  AETHER_WIFI_CONNECTED,
  AETHER_WIFI_FAIL,
} aether_wifi_state_t;

typedef struct {
  char ssid[33];
  int8_t rssi;
  uint8_t authmode; /* wifi_auth_mode_t */
} aether_wifi_ap_t;

#define AETHER_WIFI_SCAN_MAX 16

/* nvs_flash + netif + event loop + esp_wifi init. Safe to call once. */
bool aether_wifi_init(void);

/* Persist enable flag; start/stop radio. Auto-connects if SSID saved. */
bool aether_wifi_set_enabled(bool on);
bool aether_wifi_enabled(void);

/* Save credentials to NVS (and apply if radio on). pass may be empty (open). */
bool aether_wifi_set_credentials(const char *ssid, const char *pass);
void aether_wifi_get_credentials(char *ssid, size_t ssid_n, char *pass,
                                 size_t pass_n);

/* Connect now with current (or provided) credentials. */
bool aether_wifi_connect(const char *ssid, const char *pass);
bool aether_wifi_disconnect(void);

/* Non-blocking scan; results via scan_count/get after complete. */
bool aether_wifi_scan_start(void);
bool aether_wifi_scan_done(void);
int aether_wifi_scan_count(void);
bool aether_wifi_scan_get(int i, aether_wifi_ap_t *out);

aether_wifi_state_t aether_wifi_state(void);
/* Human status for UI (e.g. "connected MyNet 192.168.1.10"). */
void aether_wifi_status_line(char *buf, size_t n);
/* SSID of current association or configured target (may be empty). */
void aether_wifi_active_ssid(char *buf, size_t n);
/* IPv4 string when connected, else empty. */
void aether_wifi_ip_str(char *buf, size_t n);
int8_t aether_wifi_rssi(void);

#endif
