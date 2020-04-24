int pm8x50_port_fs_set(int unit, bcm_port_t port, int speed, int lanes, int fec, int phy_lane_config, int link_training)
{
    int rv = BCM_E_NONE;
    bcm_port_resource_t rsrc;
    bcm_port_resource_t_init(&rsrc);
    rsrc.port = port;
    rsrc.physical_port = 0; /* not used */
    rsrc.speed = speed;
    rsrc.lanes = lanes;
    rsrc.fec_type = fec;
    rsrc.phy_lane_config = phy_lane_config;
    rsrc.link_training = 0;
    rv = bcm_port_resource_speed_set(unit, port, &rsrc);

    return rv;
}

void FecSetting()
{
    int i=0;
    int logical_port[128] = {20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,
			1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,
		        80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,
			100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135};
    for(i=0;i<128;i++)
    {
        pm8x50_port_fs_set(0, logical_port[i], 100000, 2, bcmPortPhyFecRs544, -1, 0);
    }
}

FecSetting();
