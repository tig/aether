#include "gcu/ecu_client.h"

#include <stdio.h>
#include <string.h>

void gcu_ecu_client_init(gcu_ecu_client_t *c, gcu_ecu_transport_t t) {
  if (!c) {
    return;
  }
  memset(c, 0, sizeof(*c));
  c->t = t;
}

static int starts_with(const char *s, const char *pfx) {
  size_t n = strlen(pfx);
  return strncmp(s, pfx, n) == 0;
}

int gcu_ecu_hex_decode(const char *hex, uint8_t *out, size_t out_len) {
  size_t n;
  size_t i;
  if (!hex || !out) {
    return -1;
  }
  n = strlen(hex);
  if (n % 2 != 0 || n / 2 > out_len) {
    return -1;
  }
  for (i = 0; i < n; i += 2) {
    unsigned int b = 0;
    if (sscanf(hex + i, "%2x", &b) != 1) {
      return -1;
    }
    out[i / 2] = (uint8_t)b;
  }
  return (int)(n / 2);
}

int gcu_ecu_hex_encode(const uint8_t *data, size_t data_len, char *out,
                       size_t out_len) {
  size_t i;
  if (!data || !out) {
    return -1;
  }
  if (out_len < data_len * 2 + 1) {
    return -1;
  }
  for (i = 0; i < data_len; i++) {
    static const char *hexd = "0123456789abcdef";
    out[i * 2] = hexd[(data[i] >> 4) & 0xF];
    out[i * 2 + 1] = hexd[data[i] & 0xF];
  }
  out[data_len * 2] = '\0';
  return 0;
}

int gcu_ecu_cmd(gcu_ecu_client_t *c, const char *req, char *resp,
                size_t resp_len) {
  if (!c || !c->t.write_line || !c->t.read_line || !req || !resp ||
      resp_len < 2) {
    return -1;
  }
  if (c->t.write_line(c->t.ctx, req) != 0) {
    return -2;
  }
  if (c->t.read_line(c->t.ctx, resp, resp_len) != 0) {
    return -3;
  }
  if (starts_with(resp, "ERR")) {
    return -4;
  }
  return 0;
}

int gcu_ecu_ping(gcu_ecu_client_t *c) {
  char resp[64];
  if (gcu_ecu_cmd(c, "PING", resp, sizeof resp) != 0) {
    return -1;
  }
  return starts_with(resp, "PONG") ? 0 : -1;
}

int gcu_ecu_sign(gcu_ecu_client_t *c, char *sig_out, size_t sig_len) {
  char resp[128];
  const char *sig;
  if (gcu_ecu_cmd(c, "SIGN", resp, sizeof resp) != 0) {
    return -1;
  }
  if (!starts_with(resp, "SIGN ")) {
    return -1;
  }
  sig = resp + 5;
  if (sig_out && sig_len > 0) {
    snprintf(sig_out, sig_len, "%s", sig);
  }
  snprintf(c->signature, sizeof c->signature, "%s", sig);
  c->connected = 1;
  return 0;
}

int gcu_ecu_read_ram(gcu_ecu_client_t *c, int page, int off, int len, uint8_t *out,
                     size_t out_len) {
  char req[64];
  char resp[1024];
  const char *hex;
  int n;
  if (!out || (size_t)len > out_len || len < 0) {
    return -1;
  }
  snprintf(req, sizeof req, "R %d %d %d", page, off, len);
  if (gcu_ecu_cmd(c, req, resp, sizeof resp) != 0) {
    return -1;
  }
  /* R OK <hex> */
  if (!starts_with(resp, "R OK ")) {
    return -1;
  }
  hex = resp + 5;
  n = gcu_ecu_hex_decode(hex, out, out_len);
  if (n != len) {
    return -1;
  }
  return 0;
}

int gcu_ecu_write_ram(gcu_ecu_client_t *c, int page, int off, const uint8_t *data,
                      size_t data_len) {
  char hex[512];
  char req[600];
  char resp[64];
  if (!data || data_len == 0 || data_len * 2 + 1 > sizeof hex) {
    return -1;
  }
  if (gcu_ecu_hex_encode(data, data_len, hex, sizeof hex) != 0) {
    return -1;
  }
  snprintf(req, sizeof req, "W %d %d %s", page, off, hex);
  if (gcu_ecu_cmd(c, req, resp, sizeof resp) != 0) {
    return -1;
  }
  return starts_with(resp, "W OK") ? 0 : -1;
}

int gcu_ecu_burn_all(gcu_ecu_client_t *c) {
  char resp[64];
  if (gcu_ecu_cmd(c, "B ALL", resp, sizeof resp) != 0) {
    return -1;
  }
  return starts_with(resp, "B OK") ? 0 : -1;
}

int gcu_ecu_power_cycle(gcu_ecu_client_t *c) {
  char resp[64];
  if (gcu_ecu_cmd(c, "POWERCYCLE", resp, sizeof resp) != 0) {
    return -1;
  }
  return starts_with(resp, "POWERCYCLE OK") ? 0 : -1;
}

int gcu_ecu_ram_crc_all(gcu_ecu_client_t *c, char *hex8_out) {
  char resp[64];
  if (!hex8_out) {
    return -1;
  }
  if (gcu_ecu_cmd(c, "RAMCRC ALL", resp, sizeof resp) != 0) {
    return -1;
  }
  if (!starts_with(resp, "RAMCRC ")) {
    return -1;
  }
  /* "RAMCRC " is 7 chars */
  snprintf(hex8_out, 9, "%s", resp + 7);
  return 0;
}

int gcu_ecu_flash_crc_all(gcu_ecu_client_t *c, char *hex8_out) {
  char resp[64];
  if (!hex8_out) {
    return -1;
  }
  if (gcu_ecu_cmd(c, "FLASHCRC ALL", resp, sizeof resp) != 0) {
    return -1;
  }
  if (!starts_with(resp, "FLASHCRC ")) {
    return -1;
  }
  /* "FLASHCRC " is 9 chars */
  snprintf(hex8_out, 9, "%s", resp + 9);
  return 0;
}
