import boto3
import socket
import urllib3

def handler(event, context):
    
    score = 0
    score_data = {}
    score_data['totalScore'] = 0
    score_data['routeTableScore'] = 0
    score_data['securityGroupRuleScore'] = 0
    score_data['elbWorkingScore'] = 0
    count = 0
    

    ec2Client = boto3.client('ec2')

    elbClient = boto3.client('elb')
    
    VPCID = list(filter(lambda x: x['OutputKey'] == 'VPCId', event['outputs']))[0]['OutputValue']
    
    routes = ec2Client.describe_route_tables(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [ VPCID ]
            },
            {
                'Name': 'association.main',
                'Values': [ 'false' ]
            }
        ]
    )

    igw = ec2Client.describe_internet_gateways(
        Filters=[
            {
                'Name': 'attachment.vpc-id',
                'Values': [ VPCID ]
            }
        ]
    )

    IGWID = igw['InternetGateways'][0]['InternetGatewayId']

    for route in range(len(routes['RouteTables'][0]['Routes'])):
        if routes['RouteTables'][0]['Routes'][route]['DestinationCidrBlock'] == '0.0.0.0/0':
            #print (routes['RouteTables'][0]['Routes'][route]['DestinationCidrBlock']) 
            if 'GatewayId' in routes['RouteTables'][0]['Routes'][route]:
                if routes['RouteTables'][0]['Routes'][route]['GatewayId'] == IGWID:
                    score += 25
                    score_data['routeTableScore'] += 50
                    
    for route in range(len(routes['RouteTables'][1]['Routes'])):
        if routes['RouteTables'][1]['Routes'][route]['DestinationCidrBlock'] == '0.0.0.0/0':
            #print (routes['RouteTables'][0]['Routes'][route]['DestinationCidrBlock']) 
            if 'GatewayId' in routes['RouteTables'][1]['Routes'][route]:
                if routes['RouteTables'][1]['Routes'][route]['GatewayId'] == IGWID:
                    score += 25
                    score_data['routeTableScore'] += 50


    rules = ec2Client.describe_security_groups(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [ VPCID ]
            },
            {
                'Name': 'description',
                'Values': [ 'NHTLABSG' ]
            }
        ]
    )

    for rule in range (len(rules["SecurityGroups"][0]['IpPermissions'])):
        #print (rules ['SecurityGroups'][0]['IpPermissionsInress'])
        if rules['SecurityGroups'][0]['IpPermissions'][rule]['IpRanges']:
            #print (rules ['SecurityGroups'][0]['IpPermissions'][rule]['IpRanges'])
            if rules['SecurityGroups'][0]['IpPermissions'][rule]['IpRanges'][0]['CidrIp'] == "0.0.0.0/0" :
                if rules['SecurityGroups'][0]['IpPermissions'][rule]['IpProtocol'] == "tcp" :
                  if rules['SecurityGroups'][0]['IpPermissions'][rule]['FromPort'] == 80 and rules['SecurityGroups'][0]['IpPermissions'][rule]['ToPort'] == 80 :
                      score += 30
                      score_data['securityGroupRuleScore'] = 100
                  elif rules['SecurityGroups'][0]['IpPermissions'][rule]['FromPort'] == 0 and rules['SecurityGroups'][0]['IpPermissions'][rule]['ToPort'] == 65535 :
                      score += 20
                      score_data['securityGroupRuleScore'] = 60
                elif rules['SecurityGroups'][0]['IpPermissions'][rule]['IpProtocol'] == "-1" :
                    score += 10
                    score_data['securityGroupRuleScore'] = 30

    if (score_data['routeTableScore'] == 100 and score_data['securityGroupRuleScore'] > 0):
        address = list(filter(lambda x: x['OutputKey'] == 'ELBDNS', event['outputs']))[0]['OutputValue']
        port = 80
        s = socket.socket()
        s.settimeout(3)
        try:
            s.connect((address, int(port)))
            s.shutdown(socket.SHUT_RDWR)
            score += 10
            score_data['elbWorkingScore'] += 50
        except Exception as e:
            #print("something's wrong with %s:%d. Exception is %s" % (address, port, e))
            score += 0
        finally:
            s.close()
        try:
            r = urllib3.PoolManager().request('GET', 'http://'+address, timeout=1)
            if r.status == 200:
                score += 10
                score_data['elbWorkingScore'] += 50
        except:
            score += 0

    score_data['totalScore'] = score
    output={
        'totalScore' : score_data['totalScore'],
        'splitScore' : { 'Route Table Fixed' : score_data['routeTableScore'], 'Security Group Fixed' : score_data['securityGroupRuleScore'], 'ELB Working' : score_data['elbWorkingScore']}
    }
    return output