import sys
import time

from openstackclient_base.base import monkey_patch
monkey_patch()

from openstackclient_base.client_set import ClientSet
import argparse

parser = argparse.ArgumentParser(description='Spawn selenium instance in just installed cloud.')
parser.add_argument('--master', help='master node ip', default='10.0.0.103')
parser.add_argument('--tenant', help='Tenant name', default='systenant')
parser.add_argument('--login', help='login', default='admin')
parser.add_argument('--password', help='password', default='topsecret')

parser.add_argument('--net', help='Network to use with tenant', default='10.109.0.0/24')
parser.add_argument('--vlan', help='VLAN to use with network', default='3310')
parser.add_argument('--image', help='URL for image to download and register in cloud', default='http://10.100.0.3/images/selenium-server.qcow2')
cloud = parser.parse_args()


conf = {}
conf['auth_uri'] = 'http://%s:5000/v2.0/' % cloud.master
conf['tenant_name'] = cloud.tenant
conf['username'] = cloud.login
conf['password'] = cloud.password
client = ClientSet(**conf)
client.http_client.authenticate()
tenant_id = client.http_client.access["token"]["tenant"]["id"]
img_url = cloud.image
img_path = "/tmp/selenium-server.qcow2"

mynet_name = 'selenium-net'
mynet_vlan = cloud.vlan
mynet_cidr = cloud.net
myimg_name = 'selenium-img'
mysg_name = 'selenium-sg'
myinstance_name = 'selenium-instance'
timeout = 300

try:
    with open(img_path) as f: pass
    print "Image found on disk"
except IOError as e:
    import urllib
    urllib.urlretrieve(img_url, img_path)
    print "Image downloaded"


try:
    mynet = client.compute.networks.find(label=mynet_name)
    print "Net found"
except:
    mynet = client.compute.networks.create(label=mynet_name, vlan_start = mynet_vlan, cidr = mynet_cidr)
    print "Net created"


try:
    client.compute.networks.associate(mynet, tenant_id)
    print "Net associated"
except:
    pass

for img in client.glance.images.list():
    if img.name == myimg_name:
        myimg = img
        print "Image found in glance"
        break
else:
    kwargs = {
        'name': myimg_name,
        'container_format': 'ovf',
        'disk_format': 'qcow2',
        'data': open(img_path),
        'is_public': True
        }
    myimg = client.image.images.create(**kwargs)
    print "Image registered"


try:
    myflavor = client.nova.flavors.find(name="m1.medium")
except:
    print >> sys.stderr, "no m1.medium flavor"
    sys.exit(1)

try:
    mysg = client.compute.security_groups.find(name=mysg_name)
    print "SG found"
except:
    mysg = client.compute.security_groups.create(mysg_name, 'SG for selenium instance')
    print "SG created"


try:
    mysg_rule = client.compute.security_group_rules.create(mysg['id'], 'TCP', '4444', '4444', '0.0.0.0/24')
    print "Rule created"
except:
    print "Rule found"


try:
    myinstance = client.nova.servers.find(name=myinstance_name)
    print "Instance found"
except:
    ins = client.nova.servers.create(myinstance_name, myimg.id, myflavor, security_groups=[mysg.name])
    time.sleep(60)
    myinstance = client.nova.servers.find(id=ins.id)
    print "Instance spawned"


time_left = int(timeout)
while time_left > 0:
    if 'ACTIVE' in myinstance._info['status']:
        print "done"
        print "Selenium IP: %s" % myinstance._info['addresses'][mynet_name][0]['addr']
        sys.exit(0)
    time.sleep(10)
    time_left -= int(10)

print >> sys.stderr, "Instance not started"
sys.exit(1)

## Clean
#client.compute.security_groups.delete(mysg)
#client.image.images.delete(myimg)
#client.compute.networks.disassociate(mynet)
#client.compute.networks.delete(mynet)
#client.image.images.create()
