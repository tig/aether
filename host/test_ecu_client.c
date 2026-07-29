/*
 * Unit tests for portable AESP client with an in-memory mock transport.
 * No network, no Python — pure host gate.
 */
#include "gcu/ecu_client.h"

#include <stdio.h>
#include <string.h>

typedef struct {
  const char *script[16]; /* alternating expect_req, canned_resp */
  int n;
  int i;
  int fail;
  char last_req[128];
} mock_t;

static int mock_write(void *ctx, const char *line) {
  mock_t *m = (mock_t *)ctx;
  if (m->i >= m->n) {
    m->fail = 1;
    return -1;
  }
  snprintf(m->last_req, sizeof m->last_req, "%s", line);
  if (strcmp(m->script[m->i], line) != 0) {
    fprintf(stderr, "mock_write: expected %s got %s\n", m->script[m->i], line);
    m->fail = 1;
    return -1;
  }
  m->i += 1;
  return 0;
}

static int mock_read(void *ctx, char *buf, size_t buf_len) {
  mock_t *m = (mock_t *)ctx;
  if (m->i >= m->n) {
    m->fail = 1;
    return -1;
  }
  snprintf(buf, buf_len, "%s", m->script[m->i]);
  m->i += 1;
  return 0;
}

static int expect(int cond, const char *msg) {
  if (!cond) {
    fprintf(stderr, "FAIL: %s\n", msg);
    return 1;
  }
  return 0;
}

int main(void) {
  int rc = 0;
  mock_t m;
  gcu_ecu_client_t c;
  gcu_ecu_transport_t t;
  char sig[96];
  char crc[16];
  uint8_t buf[8];
  uint8_t wdata[2] = {0xef, 0xbe};

  /* hex helpers */
  {
    uint8_t out[4];
    char hex[16];
    if (expect(gcu_ecu_hex_decode("aabbcc", out, sizeof out) == 3, "hex decode len") ||
        expect(out[0] == 0xaa && out[1] == 0xbb && out[2] == 0xcc, "hex decode bytes") ||
        expect(gcu_ecu_hex_encode(out, 3, hex, sizeof hex) == 0, "hex encode") ||
        expect(strcmp(hex, "aabbcc") == 0, "hex encode value")) {
      return 1;
    }
  }

  memset(&m, 0, sizeof m);
  m.script[0] = "SIGN";
  m.script[1] = "SIGN AETHER_ECU_SIM_v1";
  m.script[2] = "W 0 0 efbe";
  m.script[3] = "W OK 2";
  m.script[4] = "R 0 0 2";
  m.script[5] = "R OK efbe";
  m.script[6] = "B ALL";
  m.script[7] = "B OK ALL";
  m.script[8] = "POWERCYCLE";
  m.script[9] = "POWERCYCLE OK";
  m.script[10] = "FLASHCRC ALL";
  m.script[11] = "FLASHCRC deadbeef";
  m.script[12] = "RAMCRC ALL";
  m.script[13] = "RAMCRC cafe0001";
  m.n = 14;
  t.write_line = mock_write;
  t.read_line = mock_read;
  t.ctx = &m;
  gcu_ecu_client_init(&c, t);

  rc |= expect(gcu_ecu_sign(&c, sig, sizeof sig) == 0, "sign ok");
  rc |= expect(strcmp(sig, "AETHER_ECU_SIM_v1") == 0, "sign value");
  rc |= expect(gcu_ecu_write_ram(&c, 0, 0, wdata, 2) == 0, "write");
  rc |= expect(gcu_ecu_read_ram(&c, 0, 0, 2, buf, sizeof buf) == 0, "read");
  rc |= expect(buf[0] == 0xef && buf[1] == 0xbe, "read bytes");
  rc |= expect(gcu_ecu_burn_all(&c) == 0, "burn");
  rc |= expect(gcu_ecu_power_cycle(&c) == 0, "powercycle");
  rc |= expect(gcu_ecu_flash_crc_all(&c, crc) == 0, "flashcrc");
  rc |= expect(strcmp(crc, "deadbeef") == 0, "flashcrc value");
  rc |= expect(gcu_ecu_ram_crc_all(&c, crc) == 0, "ramcrc");
  rc |= expect(strcmp(crc, "cafe0001") == 0, "ramcrc value");
  rc |= expect(m.i == m.n, "script exhausted");
  rc |= expect(m.fail == 0, "no mock fail");

  if (rc == 0) {
    printf("test_ecu_client: OK\n");
  }
  return rc ? 1 : 0;
}
