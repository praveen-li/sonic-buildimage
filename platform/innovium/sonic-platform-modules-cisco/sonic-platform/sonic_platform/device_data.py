DEVICE_DATA = {
    'x86_64-cisco_N3K_C3432D': {
        'globals': {
            #frontpanel port leds related
            'fp_start_index' : 1,
            'max_fp_num' : 34,

            #Thermal thresholds
            'min_temperature' : 55.0,
            'max_temperature' : 85.0,
            'min_blue_fans_speed' : 80,
            'min_red_fans_speed' : 60,
            'max_blue_fans_speed' : 100,
            'max_red_fans_speed' : 100,
            'fan_speed_tolerance' : 15,
            'fan_pwm_path_format' : 0,
            'fan_direction_format' : 1, # fan direction: 0 - b2f ; 1 - f2b
            'sensors_path_format' : 1,
            'F_fan_curve_slope' : 225.0,
            'R_fan_curve_slope' : 195.0,
            'psu_eeprom_data_format' : 0,
            'thermal_high_thresh_hysteresis' : 5.0,
            'thermal_crit_thresh_hysteresis' : 10.0,
            'blue_fans_inlet_temp_low_threshold' : 25.0,
            'red_fans_inlet_temp_low_threshold' : 25.0,
            'blue_fans_inlet_temp_high_threshold' : 35.0,
            'red_fans_inlet_temp_high_threshold' : 35.0,
            'reboot_gpio' : 133,
            'shutdown_gpio' : 134,

            #Components and their num instances in platform
            'IOFPGA' : 1,
            'MIFPGA' : 1,
            'BIOS'   : 2  #num partitions
        },
        'fans': {
            'drawer_num': 6,
            'fan_drawer': [{'fan_num': 2, 'fan':[{'bus': 31, 'addr': "002f", 'input_index': 1, 'gpio_presence': 804, 'gpio_direction': 800},
                                                 {'bus': 31, 'addr': "002f", 'input_index': 2, 'gpio_presence': 804, 'gpio_direction': 800}]},
                           {'fan_num': 2, 'fan':[{'bus': 31, 'addr': "002f", 'input_index': 3, 'gpio_presence': 805, 'gpio_direction': 801},
                                                 {'bus': 31, 'addr': "002f", 'input_index': 4, 'gpio_presence': 805, 'gpio_direction': 801}]},
                           {'fan_num': 2, 'fan':[{'bus': 31, 'addr': "002c", 'input_index': 1, 'gpio_presence': 806, 'gpio_direction': 802},
                                                 {'bus': 31, 'addr': "002c", 'input_index': 2, 'gpio_presence': 806, 'gpio_direction': 802}]},
                           {'fan_num': 2, 'fan':[{'bus': 31, 'addr': "002c", 'input_index': 3, 'gpio_presence': 807, 'gpio_direction': 803},
                                                 {'bus': 31, 'addr': "002c", 'input_index': 4, 'gpio_presence': 807, 'gpio_direction': 803}]},
                           {'fan_num': 2, 'fan':[{'bus': 31, 'addr': "002e", 'input_index': 1, 'gpio_presence': 819, 'gpio_direction': 818},
                                                 {'bus': 31, 'addr': "002e", 'input_index': 2, 'gpio_presence': 819, 'gpio_direction': 818}]},
                           {'fan_num': 2, 'fan':[{'bus': 31, 'addr': "002e", 'input_index': 3, 'gpio_presence': 823, 'gpio_direction': 822},
                                                 {'bus': 31, 'addr': "002e", 'input_index': 4, 'gpio_presence': 823, 'gpio_direction': 822}]}]
        },
        'psus': {
            'psu_num': 2,
            'psu' : [{'bus' : 34, 'addr' : "005a", 'eeprom_addr' : "0052",'gpio' : 116,'fan_num':1,'hot_swappable':True, 'led_num' :1, 'is_fan_sw_controllable' : True},
                     {'bus' : 35, 'addr' : "005a", 'eeprom_addr' : "0052",'gpio' : 117,'fan_num':1,'hot_swappable':True, 'led_num' :1, 'is_fan_sw_controllable' : True}]

        },
        'thermals': {
            'thermal_num': 3,
            'temp' : [
                {'name' : "BACK (D1)", 'bus' : 31 , 'addr' : "0018", 'index' : 2, 'location': 'near Fans', 'minor': 70, 'major': 80},
                {'name' : "FRONT (D1)",'bus' : 40 , 'addr' : "0018", 'index' : 2, 'location': 'near front panel ports', 'minor': 42, 'major': 70},
                {'name' : "ASIC",'bus' : 40 , 'addr' : "002a", 'index' : 1, 'location': 'near ASIC', 'minor': 90, 'major': 110}
                ]
        },
        'sfps': {
            'fp_num' : 32,
            'fp_start_index' : 1,
            'sfp' : [
                {'type' : 'QSFP_DD', 'sfp_num' : 32, 'start_index' : 1},
                ]
        }
    }
}
