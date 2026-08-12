#include "afr_demo.h"
#include "afr_face.h"
#include "display.h"
#include "gcu/defaults.h"
#include "gcu/domain.h"
#include "gcu/hal.h"
#include "gcu/version.h"
#include "hal_board.h"
#include "wifi_sta.h"

#include "driver/spi_master.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esprec.h"

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/*
 * Identity on the link (#78 / #79): boot-print alone is not enough for
 * silico inspect after the greeting scrolls past. The app must also answer
 * the host word "identity" (CR/LF framed) with fw_name=… fw_version=….
 *
 * esprec (tig/esprec): host may send "shot" / "esprec shot" to capture the
 * LVGL face shadow (logical 800×480 RGB565, host-endian for RGB panel).
 *
 * stdin MUST be non-blocking before the forever loop. Blocking getchar()
 * would park app_main and kill the product face until a host line arrives.
 */
static int g_stdin_nonblock;
/* Host-endian RGB565 shadow for esprec (matches RGB panel / LVGL face). */
static uint16_t *s_shot_shadow;

static void stdin_set_nonblocking(void) {
  int flags = fcntl(STDIN_FILENO, F_GETFL, 0);
  if (flags < 0) {
    g_stdin_nonblock = 0;
    return;
  }
  if (fcntl(STDIN_FILENO, F_SETFL, flags | O_NONBLOCK) == 0) {
    g_stdin_nonblock = 1;
  } else {
    g_stdin_nonblock = 0;
  }
}

/** Pack logical RGB565 face into SPI_BE shadow for esprec_emit (tool contract). */
static int pack_shot_shadow(void) {
  const uint16_t *face = display_face_buffer();
  if (!face) {
    return -1;
  }
  if (!s_shot_shadow) {
    size_t nbytes = (size_t)FACE_W * (size_t)FACE_H * sizeof(uint16_t);
    s_shot_shadow = (uint16_t *)malloc(nbytes);
    if (!s_shot_shadow) {
      return -2;
    }
  }
  for (int i = 0; i < FACE_W * FACE_H; i++) {
    s_shot_shadow[i] = (uint16_t)SPI_SWAP_DATA_TX(face[i], 16);
  }
  return 0;
}

static void board_send_shot(void) {
  if (pack_shot_shadow() != 0) {
    printf("ESPREC1_ERR no_shadow\n");
    fflush(stdout);
    return;
  }
  /* Quiet logs so ESP_LOG* cannot interleave into the base64 payload. */
  esp_log_level_set("*", ESP_LOG_NONE);
  (void)esprec_emit_rgb565_spi_be(s_shot_shadow, FACE_W, FACE_H);
  esp_log_level_set("*", ESP_LOG_INFO);
}

static void board_esprec_rec_poll(void) {
  if (!esprec_rec_active()) {
    return;
  }
  int64_t now_ms = esp_timer_get_time() / 1000;
  if (!esprec_rec_due(now_ms)) {
    return;
  }
  if (pack_shot_shadow() != 0) {
    return;
  }
  /* Quarter-res for multi-Hz rec (same policy as xuss-c). */
  (void)esprec_rec_push_scaled(s_shot_shadow, FACE_W, FACE_H, now_ms);
}

static void board_esprec_rec_start(const char *args) {
  float hz = 5.0f;
  float sec = 3.0f;
  int max_override = 0;
  if (args && *args) {
    (void)sscanf(args, "%f %f %d", &hz, &sec, &max_override);
  }
  if (hz < 0.5f) {
    hz = 0.5f;
  }
  if (hz > 30.0f) {
    hz = 30.0f;
  }
  if (sec < 0.2f) {
    sec = 0.2f;
  }
  if (sec > 30.0f) {
    sec = 30.0f;
  }
  int interval_ms = (int)(1000.0f / hz + 0.5f);
  if (interval_ms < 33) {
    interval_ms = 33;
  }
  int max_frames = (max_override > 0) ? max_override : (int)(hz * sec + 2.5f);
  if (max_frames < 1) {
    max_frames = 1;
  }
  if (max_frames > 120) {
    max_frames = 120;
  }
  if (pack_shot_shadow() != 0) {
    printf("ESPREC1_ERR no_shadow\n");
    fflush(stdout);
    return;
  }
  /* RAM-only quarter face (112×92) — no SPIFFS required on this product yet. */
  int rw = FACE_W / 4;
  int rh = FACE_H / 4;
  if (esprec_rec_begin(rw, rh, interval_ms, max_frames, NULL) != 0) {
    printf("ESPREC1_ERR rec_begin\n");
    fflush(stdout);
    return;
  }
}

static void board_esprec_spool(void) {
  esp_log_level_set("*", ESP_LOG_NONE);
  (void)esprec_rec_spool();
  esp_log_level_set("*", ESP_LOG_INFO);
}

static void handle_line(char *line) {
  char *p = line;
  while (*p && isspace((unsigned char)*p)) {
    p++;
  }
  if (strcmp(p, "identity") == 0) {
    char id[64];
    gcu_identity_line(id, (int)sizeof id);
    printf("%s\n", id);
    fflush(stdout);
  } else if (strncmp(p, "face scene ", 11) == 0) {
    const char *id = p + 11;
    while (*id == ' ') {
      id++;
    }
    if (afr_face_apply_scene(id) == 0) {
      printf("ok face scene %s\n", id);
    } else {
      printf("err face scene unknown\n");
    }
    fflush(stdout);
  } else if (strcmp(p, "face live") == 0) {
    afr_face_live();
    printf("ok face live\n");
    fflush(stdout);
  } else if (strncmp(p, "page ", 5) == 0) {
    const char *arg = p + 5;
    while (*arg == ' ') {
      arg++;
    }
    if (strcmp(arg, "next") == 0) {
      afr_face_set_page(afr_face_page() + 1);
    } else if (strcmp(arg, "prev") == 0) {
      afr_face_set_page(afr_face_page() - 1);
    } else if (strcmp(arg, "afr") == 0 || strcmp(arg, "0") == 0) {
      afr_face_set_page(0);
    } else if (strcmp(arg, "settings") == 0 || strcmp(arg, "1") == 0) {
      afr_face_set_page(1);
    } else if (strcmp(arg, "about") == 0 || strcmp(arg, "2") == 0) {
      afr_face_set_page(2);
    } else {
      printf("err page unknown\n");
      fflush(stdout);
      return;
    }
    printf("ok page %d\n", afr_face_page());
    fflush(stdout);
  } else if (strcmp(p, "wifi") == 0 || strcmp(p, "wifi status") == 0) {
    char line[96];
    aether_wifi_status_line(line, sizeof line);
    printf("wifi %s enabled=%d\n", line, (int)aether_wifi_enabled());
    fflush(stdout);
  } else if (strcmp(p, "wifi on") == 0) {
    (void)aether_wifi_set_enabled(true);
    printf("ok wifi on\n");
    fflush(stdout);
  } else if (strcmp(p, "wifi off") == 0) {
    (void)aether_wifi_set_enabled(false);
    printf("ok wifi off\n");
    fflush(stdout);
  } else if (strncmp(p, "wifi set ", 9) == 0) {
    /* wifi set <ssid> <password>  (password may be empty) */
    const char *rest = p + 9;
    while (*rest == ' ') {
      rest++;
    }
    char ssid[33];
    char pass[65];
    ssid[0] = pass[0] = 0;
    const char *sp = strchr(rest, ' ');
    if (!sp) {
      strncpy(ssid, rest, sizeof ssid - 1);
    } else {
      size_t n = (size_t)(sp - rest);
      if (n >= sizeof ssid) {
        n = sizeof ssid - 1;
      }
      memcpy(ssid, rest, n);
      ssid[n] = 0;
      while (*sp == ' ') {
        sp++;
      }
      strncpy(pass, sp, sizeof pass - 1);
    }
    if (!ssid[0]) {
      printf("err wifi set need ssid\n");
    } else {
      (void)aether_wifi_set_credentials(ssid, pass);
      (void)aether_wifi_connect(ssid, pass);
      printf("ok wifi set %s\n", ssid);
    }
    fflush(stdout);
  } else if (strcmp(p, "wifi scan") == 0) {
    if (!aether_wifi_scan_start()) {
      printf("err wifi scan\n");
    } else {
      printf("ok wifi scan started\n");
    }
    fflush(stdout);
  } else if (strcmp(p, "shot") == 0 || strcmp(p, "frame") == 0 ||
             strcmp(p, "esprec") == 0) {
    board_send_shot();
  } else if (strncmp(p, "esprec ", 7) == 0) {
    const char *sub = p + 7;
    if (strcmp(sub, "shot") == 0) {
      board_send_shot();
    } else if (strncmp(sub, "rec start", 9) == 0) {
      const char *args = sub + 9;
      while (*args == ' ') {
        args++;
      }
      board_esprec_rec_start(args);
    } else if (strcmp(sub, "rec stop") == 0) {
      (void)esprec_rec_stop();
    } else if (strcmp(sub, "spool") == 0) {
      board_esprec_spool();
    } else if (strcmp(sub, "rec abort") == 0) {
      esprec_rec_abort();
      printf("ok rec abort\n");
      fflush(stdout);
    } else {
      printf("err esprec unknown\n");
      fflush(stdout);
    }
  }
}

static void drain_host_commands(void) {
  static char line[128];
  static int n;
  int c;

  if (!g_stdin_nonblock) {
    return;
  }

  while ((c = getchar()) != EOF) {
    if (c == '\r' || c == '\n') {
      if (n > 0) {
        line[n] = '\0';
        handle_line(line);
        n = 0;
      }
      continue;
    }
    if (n < (int)sizeof(line) - 1) {
      line[n++] = (char)c;
    } else {
      n = 0;
    }
  }
  clearerr(stdin);
  if (errno == EAGAIN || errno == EWOULDBLOCK) {
    errno = 0;
  }
}

void app_main(void) {
  char id[64];
  gcu_state_t st;
  gcu_hal_t *hal = gcu_make_board_hal();

  gcu_identity_line(id, (int)sizeof id);
  printf("%s\n", id);
  fflush(stdout);

  stdin_set_nonblocking();
  if (!g_stdin_nonblock) {
    printf("WARN: stdin not non-blocking; identity/esprec drain disabled "
           "(product face continues)\n");
    fflush(stdout);
  }

  gcu_init(&st, hal);

  /* RGB bounce buffers need internal DMA RAM. Bring the panel up before
   * esp_wifi so STA RX/TX buffers cannot starve lcd_rgb_panel_alloc. */
  printf("display: init RGB 4.3B + LVGL + esprec shadow (30s AFR demo)\n");
  fflush(stdout);
  if (!display_init()) {
    printf("display: INIT FAILED — identity loop only\n");
    fflush(stdout);
    for (;;) {
      drain_host_commands();
      gcu_tick(&st);
      if (hal && hal->delay_ms) {
        hal->delay_ms(hal, gcu_tick_sleep_ms(&st));
      }
    }
  }

  if (!display_lvgl_init()) {
    printf("display: LVGL INIT FAILED — identity loop only\n");
    fflush(stdout);
    for (;;) {
      drain_host_commands();
      gcu_tick(&st);
      if (hal && hal->delay_ms) {
        hal->delay_ms(hal, gcu_tick_sleep_ms(&st));
      }
    }
  }

  afr_face_init();

  /* NVS + esp_wifi / esp_netif after the RGB panel owns its bounce RAM. */
  if (!aether_wifi_init()) {
    printf("wifi: init failed (settings still show off)\n");
    fflush(stdout);
  }

  afr_face_state_t face_st;
  memset(&face_st, 0, sizeof face_st);

  printf("demo: 30s seamless loop (forever); host: esprec shot | face live\n");
  fflush(stdout);

  /* Demo clock starts at 0 so every boot opens on the off/crank story. */
  int64_t demo_t0 = (hal && hal->now_ms) ? hal->now_ms(hal) : 0;

  for (;;) {
    drain_host_commands();
    gcu_tick(&st);

    if (!afr_face_scene_hold()) {
      int64_t now = (hal && hal->now_ms) ? hal->now_ms(hal) : 0;
      int64_t t_demo = now - demo_t0;
      if (t_demo < 0) {
        t_demo = 0;
      }
      afr_demo_sample(t_demo, &face_st);
      afr_face_update(&face_st);
    }
    afr_face_handler();
    board_esprec_rec_poll();

    if (hal && hal->delay_ms) {
      /* ~50 Hz: better touch + tileview swipe; demo still cheap. */
      hal->delay_ms(hal, 20);
    }
  }
}
