idf_component_register(
  SRCS "main.c" "hal_board.c"
       "display.c" "afr_map.c" "afr_face.c" "afr_demo.c" "wifi_sta.c"
       "face/face_banner.c" "face/face_dial.c" "face/face_primary.c"
       "face/face_aux.c" "face/face_chrome.c"
       "face/face_settings.c" "face/face_about.c"
       "fonts/font_aether_primary_112.c"
       "fonts/font_aether_unit_36.c"
       "fonts/font_aether_aux_64.c"
       "fonts/font_aether_mark_20.c"
       "../../src/defaults.c" "../../src/domain.c"
  INCLUDE_DIRS "." "face" "fonts" "../../include"
  REQUIRES driver esp_timer esp_lcd lvgl esprec esp_lcd_touch
           nvs_flash esp_wifi esp_netif esp_event
)

# LVGL component sometimes trips -Werror=attributes on older IDF toolchains.
idf_build_get_property(build_components BUILD_COMPONENTS)
if("lvgl__lvgl" IN_LIST build_components)
  idf_component_get_property(LVGL_LIB lvgl__lvgl COMPONENT_LIB)
  if(TARGET ${LVGL_LIB})
    target_compile_options(${LVGL_LIB} PRIVATE -Wno-error=attributes)
  endif()
endif()
