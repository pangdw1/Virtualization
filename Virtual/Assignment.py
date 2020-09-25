  
import argparse
import openstack
import time

conn = openstack.connect(cloud_name='openstack')
serverList = [ "pangdw1-app", "pangdw1-db", "pangdw1-web" ]

IMAGE = 'ubuntu-minimal-16.04-x86_64'
FLAVOUR = 'c1.c1r1'
NETWORK = 'pangdw1-net'
SUBNET = 'pangdw1-subnet'
ROUTER = 'pangdw1-rtr'
SECURITY_GROUP = 'default'
KEYPAIR = 'pangdw1'

public_net = conn.network.find_network(name_or_id='public-net')
floating_ip = conn.network.create_ip(floating_network_id=public_net.id)
router = conn.network.find_router(ROUTER)
image = conn.compute.find_image(IMAGE)
flavour = conn.compute.find_flavor(FLAVOUR)
security_group = conn.network.find_security_group(SECURITY_GROUP)
keypair = conn.compute.find_keypair(KEYPAIR)

network = conn.network.find_network(NETWORK)
router = conn.network.find_router(ROUTER)
subnet = conn.network.find_subnet(SUBNET)

def create():
    ''' Create a set of Openstack resources '''
    
# Network
    print("Creating Network...")
    if conn.network.find_network(NETWORK) is None:
        network = conn.network.create_network(
            name=NETWORK)
        print("Network Successfully Created.")
    else:
        print("Network Already Exists.")
        pass

# Subnet
    print("Creating Subnet...")
    if conn.network.find_subnet(SUBNET) is None:
        subnet = conn.network.create_subnet(
            name=SUBNET,
            network_id=network.id,
            ip_version='4',
            cidr='192.168.50.0/24',
            gateway_ip='192.168.50.1')
        print("Subnet Successfully Created.")
    else:
        print("Subnet Already Exists.")
        pass
# Router
    print("Creating Router...")
    if conn.network.find_router('pangdw1') is None:
        router = conn.network.create_router(
            name='pangdw1-rtr',
            external_gateway_info={ 'network_id' : public_net.id }
        )
        print("Router successfully created.")
        conn.network.add_interface_to_router(router, subnet.id)
    else:
        print("Router already exists.")
        pass
# Launch    
    print("Launching Servers...")
    for serverName in serverList:
        if conn.compute.find_server(name_or_id=serverName) is None:
            SERVER = serverName
            server = conn.compute.create_server(
            name=SERVER, image_id=image.id, flavor_id=flavour.id,
            networks=[{"uuid": network.id}], key_name=keypair.name, security_groups=[security_group])
            server = conn.compute.wait_for_server(server)
            print(serverName + " Successfully Created.")

            if serverName == "pangdw1-web":   
                web = conn.compute.find_server("pangdw1-web")
                conn.compute.wait_for_server(server)
                conn.compute.add_floating_ip_to_server(web, floating_ip.floating_ip_address)
                print("Floating IP " + str(floating_ip.floating_ip_address) + " Applied To pangdw1-web.")
        else:
            print(serverName + " Already Exists.")
    pass
def run():
    ''' Start  a set of Openstack virtual machines
    if they are not already running.
    '''
    for name in serverList:
        server = conn.compute.find_server(name_or_id=name)
        if server is not None:
            ser = conn.compute.get_server(server)
            if ser.status == "SHUTOFF":
                print(name + " Starting Server Up...")
                conn.compute.start_server(ser)
                print(name + " Running.")
            elif ser.status == "ACTIVE":
                print(name + " Is Already Running.")
        else:
            print(name + " Does Not Exist.")
    pass
def stop():
    ''' Stop  a set of Openstack virtual machines
    if they are running.
    '''
    for name in serverList:
        server = conn.compute.find_server(name_or_id=name)
        if server is not None:
            ser = conn.compute.get_server(server)
            if ser.status == "ACTIVE":
                print(name + " Stopping Server...")
                conn.compute.stop_server(ser)
                print(name + " Stopped.")
            elif ser.status == "SHUTOFF":
                print(name + " Is Already Off.")
        else:
            print(name + " Does Not Exist.")
    pass
def destroy():
    ''' Tear down the set of Openstack resources 
    produced by the create action
    '''
    for server in serverList:
        ser = conn.compute.find_server(name_or_id=server)
        if ser is not None:
            if server == 'pangdw1-web':
                dserver = conn.compute.get_server(ser)
                server_floating_ip = dserver['addresses'][NETWORK][1]['addr']
                print("Removing Floating IP")
                conn.compute.remove_floating_ip_from_server(dserver, server_floating_ip)

                print("Floating IP Removed From " + ser.name)
                drop_ip = conn.network.find_ip(server_floating_ip)
                conn.network.delete_ip(drop_ip)
                time.sleep(3)
                print("IP Dropped")

            conn.compute.delete_server(ser)

            print(ser.name + " Destroyed.")
        else:
            print(server + " Does Not Exist.")

    # Destroy router
    if router is not None:
        conn.network.remove_interface_from_router(router, subnet.id)
        conn.network.delete_router(router)
        time.sleep(3)
        print("Router Destroyed")
    else:
        print("Network Does Not Exist.")

    # destory subnet
    if subnet is not None:
        conn.network.delete_subnet(subnet)
        time.sleep(3)
        print("Subnet Destroyed")
    else:
        print("Subnet Does Not Exist.")

    # destroy network
    network = conn.network.find_network("pangdw1-net")
    if network is not None:
        delNetwork = conn.network.delete_network(network)
        conn.network.delete_network(network)
        time.sleep(3)
        print("Network Destroyed")
    else:
        print("Network Does Not Exist.")
    pass

def status():
    ''' Print a status report on the OpenStack
    virtual machines created by the create action.
    '''
    for server in serverList:
        serverid = conn.compute.find_server(name_or_id=server)
        if serverid is None:
            print(server + " Does Not Exist.")
        elif serverid is not None:
            ser = conn.compute.get_server(serverid)
            print("Name: " + ser.name + "\n"
                "Status: " + ser.status)
            for value in ser.addresses[NETWORK]:
                print("IP: " + value["addr"])
        print("\n")
    pass


### You should not modify anything below this line ###
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation',
                        help='One of "create", "run", "stop", "destroy", or "status"')
    args = parser.parse_args()
    operation = args.operation
    operations = {
        'create'  : create,
        'run'     : run,
        'stop'    : stop,
        'destroy' : destroy,
        'status'  : status
        }

    action = operations.get(operation, lambda: print('{}: no such operation'.format(operation)))
    action()