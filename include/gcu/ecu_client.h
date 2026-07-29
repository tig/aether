#ifndef GCU_ECU_CLIENT_H
#define GCU_ECU_CLIENT_H

/*
 * Portable AESP ECU client (software V-ECU first; TS binary later).
 *
 * Domain-safe: no freertos / esp_* / driver headers. Transport is injected
 * so host tests use TCP sockets and metal can later use UART.
 */

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Line transport: write a full request line (without trailing NL). */
typedef int (*gcu_ecu_write_line_fn)(void *ctx, const char *line);

/**
 * Read one response line into buf (NUL-terminated, without CR/LF).
 * Returns 0 on success, non-zero on error / timeout / EOF.
 */
typedef int (*gcu_ecu_read_line_fn)(void *ctx, char *buf, size_t buf_len);

typedef struct {
  gcu_ecu_write_line_fn write_line;
  gcu_ecu_read_line_fn read_line;
  void *ctx;
} gcu_ecu_transport_t;

typedef struct {
  gcu_ecu_transport_t t;
  int connected; /* 1 after successful SIGN (or after greeting skip by caller) */
  char signature[96];
} gcu_ecu_client_t;

void gcu_ecu_client_init(gcu_ecu_client_t *c, gcu_ecu_transport_t t);

/** Send raw AESP command; response (without NL) written to resp. */
int gcu_ecu_cmd(gcu_ecu_client_t *c, const char *req, char *resp, size_t resp_len);

int gcu_ecu_ping(gcu_ecu_client_t *c);
int gcu_ecu_sign(gcu_ecu_client_t *c, char *sig_out, size_t sig_len);
int gcu_ecu_read_ram(gcu_ecu_client_t *c, int page, int off, int len, uint8_t *out,
                     size_t out_len);
int gcu_ecu_write_ram(gcu_ecu_client_t *c, int page, int off, const uint8_t *data,
                      size_t data_len);
int gcu_ecu_burn_all(gcu_ecu_client_t *c);
int gcu_ecu_power_cycle(gcu_ecu_client_t *c);
int gcu_ecu_ram_crc_all(gcu_ecu_client_t *c, char *hex8_out /* at least 9 bytes */);
int gcu_ecu_flash_crc_all(gcu_ecu_client_t *c, char *hex8_out);

/** Decode lowercase/uppercase hex into out; returns byte count or -1. */
int gcu_ecu_hex_decode(const char *hex, uint8_t *out, size_t out_len);

/** Encode bytes to lowercase hex; writes NUL; returns 0 or -1 if too small. */
int gcu_ecu_hex_encode(const uint8_t *data, size_t data_len, char *out,
                       size_t out_len);

#ifdef __cplusplus
}
#endif

#endif /* GCU_ECU_CLIENT_H */
