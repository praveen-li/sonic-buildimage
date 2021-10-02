DEVICE_DATA = {
    'x86_64-n3200-r0':{
        'globals': {
            #frontpanel port leds related
            'fp_start_index' : 1,
            'max_fp_num' : 32,

            #Thermal thresholds
            'min_temperature_threshold' : 55.0, 
            'max_temperature_threshold' : 85.0,
            'min_blue_fans_speed' : 60,
            'min_red_fans_speed' : 60,
            'max_blue_fans_speed' : 100, 
            'max_red_fans_speed' : 100,
            'fan_speed_tolerance' : 25,
            'fan_pwm_path_format' : 2,
            'sensors_path_format' : 1,
            'F_fan_curve_slope' : 153.0,
            'R_fan_curve_slope' : 113.0,
            'psu_eeprom_data_format' : 0,
            'thermal_high_thresh_hysteresis' : 5.0,
            'thermal_crit_thresh_hysteresis' : 10.0,
            'blue_fans_inlet_temp_threshold' : 35.0,
            'red_fans_inlet_temp_threshold' : 35.0,
            'reboot_gpio' : 133,
            'shutdown_gpio' : 134,
            'transceiver_enable_high_power_class': 1,
            'max_supplied_power' : 650.0,

            #Components and their num instances in platform
            'IOFPGA' : 1,
            'MIFPGA' : 1,
            'BIOS'   : 2  #num partitions
        },
        'fans': {
            'drawer_num': 4,
            'fan_drawer': [{'fan_num' : 2,
                            'fan':[{'bus': 31,'addr' : "0058",'gpio_presence' : 500,'gpio_direction' :496 },
                                   {'bus': 31,'addr' : "0058",'gpio_presence' : 500,'gpio_direction' :496 }]},
                           {'fan_num' : 2,
                            'fan':[{'bus': 31,'addr' : "0058",'gpio_presence' : 501,'gpio_direction' :497 },
                                   {'bus': 31,'addr' : "0058",'gpio_presence' : 501,'gpio_direction' :497 }]},
                           {'fan_num' : 2,
                            'fan':[{'bus': 31,'addr' : "0058",'gpio_presence' : 502,'gpio_direction' :498 },
                                   {'bus': 31,'addr' : "0058",'gpio_presence' : 502,'gpio_direction' :498 }]},
                           {'fan_num' : 2,
                            'fan':[{'bus': 31,'addr' : "0058",'gpio_presence' : 503,'gpio_direction' :499 },
                                   {'bus': 31,'addr' : "0058",'gpio_presence' : 503,'gpio_direction' :499 }]},
                          ]
        },
        'psus': {
            'psu_num': 2,
            'psu' : [{'bus' : 34, 'addr' : "0058", 'eeprom_addr' : "0050",'gpio' : 116, 'fan_num':1,'hot_swappable': True,'led_num' :1, 'is_fan_sw_controllable' : False},
                {'bus' : 35, 'addr' : "0058", 'eeprom_addr' : "0050",'gpio' : 117, 'fan_num':1,'hot_swappable': True,'led_num' :1, 'is_fan_sw_controllable' : False}]
        },
        'thermals': {
            'thermal_num': 3,
            'temp' : [{'name' : "FRONT(D0)", 'bus' : 31 , 'addr' : "0058", 'index' : 2, 'location': 'near Fans', 'minor': 70, 'major':80},
            {'name' : "BACK(D1)", 'bus' : 31 , 'addr' : "0058", 'index' : 3, 'location': 'near front panel ports', 'minor':90, 'major':105},
        {'name' : "BACK(D2)", 'bus' : 31 , 'addr' : "0058", 'index' : 0, 'location': 'near front panel ports', 'minor':42, 'major': 60}]
        },
        'sfps':{
            'fp_num' : 32,
            'fp_start_index' : 1,
            'sfp' : [
                {'type' : 'QSFP', 'sfp_num' : 32, 'start_index' : 1},
                {'type' : 'SFP', 'sfp_num' : 0, 'start_index' : 0}
                ]
        }
    }
}
