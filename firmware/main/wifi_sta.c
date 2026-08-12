/* Wi-Fi station — ESP-IDF esp_wifi / esp_netif / nvs_flash only. */
#include "wifi_sta.h"

#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "nvs.h"
#include "nvs_flash.h"

#include <stdio.h>
#include <string.h>

static const char *TAG = "wifi_sta";
static const char *NVS_NS = "aether_wifi";

static bool s_inited;
static bool s_enabled;
static bool s_scan_done;
static int s_retry;
static aether_wifi_state_t s_state = AETHER_WIFI_OFF;
static esp_netif_t *s_netif;
static char s_ssid[33];
static char s_pass[65];
static char s_ip[16];
static aether_wifi_ap_t s_aps[AETHER_WIFI_SCAN_MAX];
static int s_ap_n;

static void nvs_load(void) {
  nvs_handle_t h;
  if (nvs_open(NVS_NS, NVS_READONLY, &h) != ESP_OK) {
    return;
  }
  size_t n = sizeof s_ssid;
  (void)nvs_get_str(h, "ssid", s_ssid, &n);
  n = sizeof s_pass;
  (void)nvs_get_str(h, "pass", s_pass, &n);
  uint8_t en = 0;
  if (nvs_get_u8(h, "enabled", &en) == ESP_OK) {
    s_enabled = en != 0;
  }
  nvs_close(h);
}

static void nvs_save_creds(void) {
  nvs_handle_t h;
  if (nvs_open(NVS_NS, NVS_READWRITE, &h) != ESP_OK) {
    return;
  }
  (void)nvs_set_str(h, "ssid", s_ssid);
  (void)nvs_set_str(h, "pass", s_pass);
  (void)nvs_commit(h);
  nvs_close(h);
}

static void nvs_save_enabled(void) {
  nvs_handle_t h;
  if (nvs_open(NVS_NS, NVS_READWRITE, &h) != ESP_OK) {
    return;
  }
  (void)nvs_set_u8(h, "enabled", s_enabled ? 1 : 0);
  (void)nvs_commit(h);
  nvs_close(h);
}

static void apply_sta_config(void) {
  wifi_config_t cfg;
  memset(&cfg, 0, sizeof cfg);
  strncpy((char *)cfg.sta.ssid, s_ssid, sizeof cfg.sta.ssid - 1);
  strncpy((char *)cfg.sta.password, s_pass, sizeof cfg.sta.password - 1);
  cfg.sta.threshold.authmode =
      s_pass[0] ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;
  cfg.sta.sae_pwe_h2e = WPA3_SAE_PWE_BOTH;
  ESP_ERROR_CHECK_WITHOUT_ABORT(esp_wifi_set_config(WIFI_IF_STA, &cfg));
}

static void on_wifi_event(void *arg, esp_event_base_t base, int32_t id,
                          void *data) {
  (void)arg;
  (void)base;
  if (id == WIFI_EVENT_STA_START) {
    if (s_enabled && s_ssid[0]) {
      s_state = AETHER_WIFI_CONNECTING;
      s_retry = 0;
      esp_wifi_connect();
    } else {
      s_state = AETHER_WIFI_DISCONNECTED;
    }
  } else if (id == WIFI_EVENT_STA_DISCONNECTED) {
    s_ip[0] = 0;
    if (s_enabled && s_ssid[0] && s_retry < 8) {
      s_retry++;
      s_state = AETHER_WIFI_CONNECTING;
      esp_wifi_connect();
      ESP_LOGI(TAG, "reconnect %d/8", s_retry);
    } else if (s_enabled) {
      s_state = AETHER_WIFI_FAIL;
    } else {
      s_state = AETHER_WIFI_DISCONNECTED;
    }
  } else if (id == WIFI_EVENT_SCAN_DONE) {
    /* Pull a wider raw set, then collapse to unique SSIDs (best RSSI). */
    enum { RAW_MAX = 48 };
    uint16_t n = RAW_MAX;
    wifi_ap_record_t rec[RAW_MAX];
    memset(rec, 0, sizeof rec);
    s_ap_n = 0;
    if (esp_wifi_scan_get_ap_records(&n, rec) == ESP_OK) {
      for (uint16_t i = 0; i < n; i++) {
        if (!rec[i].ssid[0]) {
          continue; /* hidden / empty */
        }
        int found = -1;
        for (int j = 0; j < s_ap_n; j++) {
          if (strncmp(s_aps[j].ssid, (const char *)rec[i].ssid,
                      sizeof s_aps[j].ssid) == 0) {
            found = j;
            break;
          }
        }
        if (found >= 0) {
          /* Keep strongest BSSID for this SSID. */
          if (rec[i].rssi > s_aps[found].rssi) {
            s_aps[found].rssi = rec[i].rssi;
            s_aps[found].authmode = (uint8_t)rec[i].authmode;
          }
        } else if (s_ap_n < AETHER_WIFI_SCAN_MAX) {
          strncpy(s_aps[s_ap_n].ssid, (const char *)rec[i].ssid,
                  sizeof s_aps[s_ap_n].ssid - 1);
          s_aps[s_ap_n].ssid[sizeof s_aps[s_ap_n].ssid - 1] = 0;
          s_aps[s_ap_n].rssi = rec[i].rssi;
          s_aps[s_ap_n].authmode = (uint8_t)rec[i].authmode;
          s_ap_n++;
        }
      }
      /* Strongest first. */
      for (int a = 0; a < s_ap_n; a++) {
        for (int b = a + 1; b < s_ap_n; b++) {
          if (s_aps[b].rssi > s_aps[a].rssi) {
            aether_wifi_ap_t tmp = s_aps[a];
            s_aps[a] = s_aps[b];
            s_aps[b] = tmp;
          }
        }
      }
    }
    s_scan_done = true;
    if (s_state == AETHER_WIFI_SCANNING) {
      s_state = s_ip[0] ? AETHER_WIFI_CONNECTED : AETHER_WIFI_DISCONNECTED;
    }
    ESP_LOGI(TAG, "scan done: %d unique SSIDs (raw %u)", s_ap_n, (unsigned)n);
  }
}

static void on_ip_event(void *arg, esp_event_base_t base, int32_t id,
                        void *data) {
  (void)arg;
  (void)base;
  if (id == IP_EVENT_STA_GOT_IP) {
    ip_event_got_ip_t *e = (ip_event_got_ip_t *)data;
    snprintf(s_ip, sizeof s_ip, IPSTR, IP2STR(&e->ip_info.ip));
    s_retry = 0;
    s_state = AETHER_WIFI_CONNECTED;
    ESP_LOGI(TAG, "got ip %s ssid=%s", s_ip, s_ssid);
  }
}

bool aether_wifi_init(void) {
  if (s_inited) {
    return true;
  }

  esp_err_t err = nvs_flash_init();
  if (err == ESP_ERR_NVS_NO_FREE_PAGES ||
      err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    err = nvs_flash_init();
  }
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "nvs_flash_init: %s", esp_err_to_name(err));
    return false;
  }

  nvs_load();

  ESP_ERROR_CHECK(esp_netif_init());
  err = esp_event_loop_create_default();
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
    ESP_LOGE(TAG, "event loop: %s", esp_err_to_name(err));
    return false;
  }
  s_netif = esp_netif_create_default_wifi_sta();
  if (!s_netif) {
    ESP_LOGE(TAG, "create default wifi sta failed");
    return false;
  }

  wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
  ESP_ERROR_CHECK(esp_wifi_init(&cfg));
  ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                             &on_wifi_event, NULL));
  ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                             &on_ip_event, NULL));
  ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
  apply_sta_config();

  s_inited = true;
  s_state = AETHER_WIFI_OFF;
  ESP_LOGI(TAG, "init ok (enabled=%d ssid=%s)", (int)s_enabled, s_ssid);

  if (s_enabled) {
    (void)aether_wifi_set_enabled(true);
  }
  return true;
}

bool aether_wifi_set_enabled(bool on) {
  if (!s_inited && !aether_wifi_init()) {
    return false;
  }
  s_enabled = on;
  nvs_save_enabled();

  if (on) {
    s_state = AETHER_WIFI_STARTING;
    s_retry = 0;
    esp_err_t err = esp_wifi_start();
    if (err != ESP_OK && err != ESP_ERR_WIFI_CONN) {
      /* Already started is OK on some paths. */
      if (err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "wifi_start: %s", esp_err_to_name(err));
      }
    }
    if (s_ssid[0]) {
      apply_sta_config();
      s_state = AETHER_WIFI_CONNECTING;
      (void)esp_wifi_connect();
    } else {
      s_state = AETHER_WIFI_DISCONNECTED;
    }
  } else {
    (void)esp_wifi_disconnect();
    (void)esp_wifi_stop();
    s_ip[0] = 0;
    s_state = AETHER_WIFI_OFF;
  }
  return true;
}

bool aether_wifi_enabled(void) { return s_enabled; }

bool aether_wifi_set_credentials(const char *ssid, const char *pass) {
  if (!ssid) {
    return false;
  }
  strncpy(s_ssid, ssid, sizeof s_ssid - 1);
  s_ssid[sizeof s_ssid - 1] = 0;
  if (pass) {
    strncpy(s_pass, pass, sizeof s_pass - 1);
    s_pass[sizeof s_pass - 1] = 0;
  } else {
    s_pass[0] = 0;
  }
  nvs_save_creds();
  if (s_inited) {
    apply_sta_config();
  }
  return true;
}

void aether_wifi_get_credentials(char *ssid, size_t ssid_n, char *pass,
                              size_t pass_n) {
  if (ssid && ssid_n) {
    strncpy(ssid, s_ssid, ssid_n - 1);
    ssid[ssid_n - 1] = 0;
  }
  if (pass && pass_n) {
    strncpy(pass, s_pass, pass_n - 1);
    pass[pass_n - 1] = 0;
  }
}

bool aether_wifi_connect(const char *ssid, const char *pass) {
  if (ssid && ssid[0]) {
    (void)aether_wifi_set_credentials(ssid, pass ? pass : "");
  }
  if (!s_ssid[0]) {
    return false;
  }
  if (!s_enabled) {
    (void)aether_wifi_set_enabled(true);
  } else {
    apply_sta_config();
    s_retry = 0;
    s_state = AETHER_WIFI_CONNECTING;
    esp_err_t err = esp_wifi_connect();
    if (err != ESP_OK && err != ESP_ERR_WIFI_CONN) {
      ESP_LOGW(TAG, "connect: %s", esp_err_to_name(err));
      return false;
    }
  }
  return true;
}

bool aether_wifi_disconnect(void) {
  s_ip[0] = 0;
  esp_err_t err = esp_wifi_disconnect();
  if (s_enabled) {
    s_state = AETHER_WIFI_DISCONNECTED;
  }
  return err == ESP_OK || err == ESP_ERR_WIFI_NOT_STARTED;
}

bool aether_wifi_scan_start(void) {
  if (!s_inited && !aether_wifi_init()) {
    return false;
  }
  if (!s_enabled) {
    /* Radio must be up to scan. */
    s_enabled = true;
    nvs_save_enabled();
    s_state = AETHER_WIFI_STARTING;
    (void)esp_wifi_start();
  }
  s_scan_done = false;
  s_ap_n = 0;
  s_state = AETHER_WIFI_SCANNING;
  wifi_scan_config_t sc = {
      .ssid = NULL,
      .bssid = NULL,
      .channel = 0,
      .show_hidden = false,
      .scan_type = WIFI_SCAN_TYPE_ACTIVE,
  };
  esp_err_t err = esp_wifi_scan_start(&sc, false);
  if (err != ESP_OK) {
    ESP_LOGW(TAG, "scan_start: %s", esp_err_to_name(err));
    s_state = AETHER_WIFI_DISCONNECTED;
    return false;
  }
  return true;
}

bool aether_wifi_scan_done(void) { return s_scan_done; }

int aether_wifi_scan_count(void) { return s_ap_n; }

bool aether_wifi_scan_get(int i, aether_wifi_ap_t *out) {
  if (!out || i < 0 || i >= s_ap_n) {
    return false;
  }
  *out = s_aps[i];
  return true;
}

aether_wifi_state_t aether_wifi_state(void) { return s_state; }

void aether_wifi_active_ssid(char *buf, size_t n) {
  if (!buf || !n) {
    return;
  }
  strncpy(buf, s_ssid, n - 1);
  buf[n - 1] = 0;
}

void aether_wifi_ip_str(char *buf, size_t n) {
  if (!buf || !n) {
    return;
  }
  strncpy(buf, s_ip, n - 1);
  buf[n - 1] = 0;
}

int8_t aether_wifi_rssi(void) {
  if (s_state != AETHER_WIFI_CONNECTED) {
    return 0;
  }
  wifi_ap_record_t ap;
  if (esp_wifi_sta_get_ap_info(&ap) != ESP_OK) {
    return 0;
  }
  return ap.rssi;
}

void aether_wifi_status_line(char *buf, size_t n) {
  if (!buf || !n) {
    return;
  }
  switch (s_state) {
  case AETHER_WIFI_OFF:
    snprintf(buf, n, "off");
    break;
  case AETHER_WIFI_STARTING:
    snprintf(buf, n, "starting…");
    break;
  case AETHER_WIFI_DISCONNECTED:
    if (s_ssid[0]) {
      snprintf(buf, n, "idle · %s", s_ssid);
    } else {
      snprintf(buf, n, "no network");
    }
    break;
  case AETHER_WIFI_SCANNING:
    snprintf(buf, n, "scanning…");
    break;
  case AETHER_WIFI_CONNECTING:
    snprintf(buf, n, "connecting %s…", s_ssid);
    break;
  case AETHER_WIFI_CONNECTED:
    snprintf(buf, n, "%s · %s", s_ssid, s_ip[0] ? s_ip : "up");
    break;
  case AETHER_WIFI_FAIL:
    snprintf(buf, n, "failed · %s", s_ssid[0] ? s_ssid : "?");
    break;
  default:
    snprintf(buf, n, "?");
    break;
  }
}
