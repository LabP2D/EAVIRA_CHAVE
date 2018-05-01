#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CHAVE-Sim: The simulator for research based in clouds architecture
    CHAVE: Consolidation with High Availability on virtualyzed environments
"""
from json import load

__author__ = "Daniel Camargo and Denivy Ruck"
__license__ = "GPL-v3"
__version__ = "2.0.1"
__maintainer__ = "Daniel Camargo"
__email__ = "daniel@colmeia.udesc.br"
__status__ = "Test"

import argparse
import logging
from datetime import datetime
import time
# From packages:
from src.Chave import *
from src.Controller import *
from src.DistInfra import *
from src.Demand import *
from src.Eucalyptus import *
from src.SLAHelper import *



def main():
    # Setting objects demand, az, lc, region, gc
    demand = Demand(sla)
    demand.create_vms_from_sources()
    # Get specific values using dict: 'all_xx_dict['DSn']'
    # print len(demand.all_operations_dicts), len(demand.all_vms_dict), len(demand.all_ha_dict)

    az_list, demand_list = [], []
    for i, azid in enumerate(demand.az_id):
        vm, op, ha = demand.get_demand_from_az(azid)

        az = AvailabilityZone(sla, azid, vm, op, ha)
        if az.create_infrastructure(first_time=True):
            az_list.append(az)
        else:
            logger.error("Problem on create infra for AZ#%s: %s" % (i, azid))

    lcontroller_list = [LocalController(sla, "lc0", az_list[0:3]),
                        LocalController(sla, "lc1", az_list[3:5])]

    region_list = [Region(sla, "r0", lcontroller_list[0]),
                   Region(sla, "r1", lcontroller_list[1])]

    '''
    ctrl = Controller(sla)
    localcontroller_list = ctrl.create_lcontroller_list(az_list)

    infra = Infrastructure(sla)
    regions_list = infra.create_regions_list(localcontroller_list)
    '''
    global_controller = GlobalController(sla, demand, lcontroller_list, region_list)

    print global_controller.localcontroller_list[0].get_vm_object_from_az('i-ABC443B3', 'DS1')

    # ################### the kernel ###############
    start = time.time()
    if sla.algorithm == "CHAVE":
        chave = Chave(sla, global_controller)
        chave.run()
    elif sla.algorithm == "EUCA":
        euca = Eucalyptus(sla)
        global_controller.run_algorithm_object(euca)
    elif sla.algorithm == "MM":
        mm = 1
        global_controller.run_algorithm_object(mm)
    elif sla.algorithm == "MBFD":
        mbfd = 1
        global_controller.run_algorithm_object(mbfd)
    elapsed = time.time() - start
    # ################### the kernel ###############

    slav = global_controller.get_total_SLA_violations_from_cloud()
    energy = global_controller.get_total_energy_consumption_from_cloud()
    overb_list = global_controller.get_list_overb_amount_from_cloud()

    # TODO:
    max_hosts_on = 0

    with open(sla.data_output, 'aw') as data:
        data.write('%s\t%s\t%s\n$s\n%s\n%s' % (slav, energy, overb_list, elapsed, max_hosts_on))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CHAVE Simulator')
    parser.add_argument('-nit', dest='nit', action='store', nargs='+', required=True,
                        help='Number of iterations: N')
    parser.add_argument('-alg', dest='alg', action='store', nargs=1, type=str, required=True,
                        help='algorithm type: CHAVE | EUCA')
    parser.add_argument('-pm', dest='pm', action='store', nargs=1, type=str, required=True,
                        help='placement or migration')
    parser.add_argument('-ff', dest='ff', action='store', nargs=1, type=str, required=True,
                        help='first fit algorithm')
    parser.add_argument('-in', dest='input', action='store', nargs='+', required=True,
                        help='Input file')
    parser.add_argument('-az', dest='az_conf', action='store', nargs='+', required=True,
                        help='AZ configuration')
    parser.add_argument('-ha', dest='ha_input', action='store', nargs='+', required=False,
                        help='High Availability from AZs')
    parser.add_argument('-wt', dest='wt', action='store', nargs=1, type=int, required=True,
                        help='Window time: N')
    parser.add_argument('-ws', dest='ws', action='store', nargs=1, type=int, required=True,
                        help='Window size: N')
    parser.add_argument('-ob', dest='overb', action='store', nargs=1, type=bool, required=True,
                        help='Has Overbooking?')
    args = parser.parse_args()
    #print args
    ''' This 'sla' instance will get all specifications and parameters'''
    sla = SLAHelper()

    sla.list_of_source_files = args.input  # List
    s = len(sla.list_of_source_files)
    if s == len(args.ha_input) == len(args.az_conf) == len(args.nit):
        sla.number_of_azs = s
    sla.ha_input = args.ha_input  # List
    sla.az_conf = sla.set_conf(args.az_conf, 'az_conf')
    sla.nit = sla.set_conf(args.nit, 'nit')
    sla.define_az_id()

    # Values from python args
    sla.pm = args.pm
    sla.ff = args.ff
    sla.has_overbooking = args.overb
    sla.algorithm = args.alg[0]
    sla.window_time = args.wt
    sla.window_size = args.ws

    # Linux Environment vars
    sla.max_az_per_region = int(os.environ["CS_MAX_AZ_REGION"])
    sla.date = datetime.now().strftime(os.environ["CS_DP"])
    sla.core2ram = os.environ.get('CS_CORE2RAM')
    sla.vm_ram_default = int(sla.core2ram.split(':')[1])
    sla.data_output = eval(os.environ["CS_DATAOUTPUT"])
    sla.log_output = eval(os.environ["CS_LOGOUTPUT"])
    sla.trigger_to_migrate = int(os.environ.get('CS_TRIGGER_MIGRATE'))
    sla.frag_percentual = float(os.environ.get('CS_FRAG_PERCENT'))

    # Para os logs de mensagens:
    logger = logging.getLogger(__name__)
    hdlr = logging.FileHandler(sla.log_output)
    hdlr.setFormatter(logging.Formatter(os.environ["CS_LOGFORMATTER"]))
    logger.addHandler(hdlr)
    # se primeiro parametro der erro, use o segundo:
    logger.setLevel(int(os.environ.get('CS_LOGLEVEL', logging.DEBUG)))
    sla.logger = logger

    main()
