import boto3

def handler(event, context):
    # event={"challengeStartTime":1533787156256,"attemptID":"a-p7quocxf","stackID":"arn:aws:cloudformation:ap-south-1:749334262463:stack/bottlenose-a-p7quocxf/dda330f0-9b87-11e8-a1ac-504dccc1c856","createdAt":1533786847977,"score":0,"user":"<alias>","challengeEndTime":1533788956256,"durationAllotted":1800000,"outputs":[{"OutputKey":"ConsoleAccessURL","OutputValue":"https://<account-id>.signin.aws.amazon.com/console?region=ap-south-1","Description":"URL to allow the user to log into the console"},{"OutputKey":"EC2InstanceId","OutputValue":"i-07308ed69ad0f469b","Description":"InstanceId of the newly created EC2 instance"},{"OutputKey":"DefaultConsoleAccessPassword","OutputValue":"<password>","Description":"Password to allow the user to log into the console"},{"OutputKey":"InstanceIpAddress","OutputValue":"52.200.223.54","Description":"IP address of the newly created EC2 instance"},{"OutputKey":"ConsoleAccessUsername","OutputValue":"<username>","Description":"Username to allow the user to log into the console"},{"OutputKey":"InstancePrivateKey","OutputValue":"-----BEGIN RSA PRIVATE KEY-----\nabcdefghijklmnopqrstuvwxyz==\n-----END RSA PRIVATE KEY-----","Description":"Private key of the newly created EC2 instance"},{"OutputKey":"Route53HostedZoneID","OutputValue":"Z06367043I4AIVGR7QUL0","Description":""},{"OutputKey":"VPCId","OutputValue":"vpc-0bc5ae6940bab730d","Description":""},{"OutputKey":"TargetGroupArn","OutputValue":"arn:aws:elasticloadbalancing:us-east-1:784439035548:targetgroup/My-NLB-CFN-TG/ec7985658b338dc7","Description":""}],"stackState":"CREATE_COMPLETE","updatedAt":1533787156256,"attemptStatus":"validating","id":"c-1618fa5a:<alias>","stackRequestTime":1533786847977}
    ec2Client = boto3.client('ec2')
    elbClient = boto3.client('elbv2')

    score = 0
    score_data = {}
    score_data['totalScore'] = 0
    score_data['securityGroupRuleScore'] = 0
    score_data['elbHealthCheckScore'] = 0
    score_data['elbWorkingScore'] = 0    

    VPCID = list(filter(lambda x: x['OutputKey'] == 'VPCId', event['outputs']))[0]['OutputValue']

    # SG
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

    nlb_nic = ec2Client.describe_network_interfaces(
        Filters=[
            {
                'Name': 'description',
                'Values': [ 'ELB net/MyNLB-CFN/fd3214fe1fcf4028' ]
            }
        ]    
    )

    nlb_private_ips = {
        nlb_nic['NetworkInterfaces'][0]['PrivateIpAddresses'][0]['PrivateIpAddress'],
        nlb_nic['NetworkInterfaces'][1]['PrivateIpAddresses'][0]['PrivateIpAddress']
    }

    flag_multiple_sg_inbound_rules = False
    if len(rules['SecurityGroups'][0]['IpPermissions']) > 1:
        flag_multiple_sg_inbound_rules = True

    for inboundrule in rules['SecurityGroups'][0]['IpPermissions']:
        cidr_ips = set()
        for ip_ranges in inboundrule['IpRanges']:
            cidr_ips.add(ip_ranges['CidrIp'][:-3])
        if cidr_ips.intersection(nlb_private_ips) == nlb_private_ips:
            if inboundrule['IpProtocol'] == 'tcp':
                if inboundrule['FromPort'] == 80 == inboundrule['ToPort']:
                    score = 40
                    score_data['securityGroupRuleScore'] = 100
                elif inboundrule['FromPort'] <= 80 <= inboundrule['ToPort']:
                    score = 20
                    score_data['securityGroupRuleScore'] = 60
            elif inboundrule['IpProtocol'] == '-1':
                score = 10
                score_data['securityGroupRuleScore'] = 30
            if cidr_ips != nlb_private_ips:
                score -= 5
                score_data['securityGroupRuleScore'] -= 20

    if (score_data['securityGroupRuleScore'] > 0 and flag_multiple_sg_inbound_rules):
        score_data['securityGroupRuleScore'] -= 20
        score -= 5

    # HC port
    target_groups = elbClient.describe_target_groups(
                TargetGroupArns=[list(filter(lambda x: x['OutputKey'] == 'TargetGroupArn', event['outputs']))[0]['OutputValue']])
    if target_groups['TargetGroups'][0]['HealthCheckPort'] == '80':
        score += 30
        score_data['elbHealthCheckScore'] = 100

    # NLB proxy_protocol_v2
    if (score_data['securityGroupRuleScore'] > 0 and score_data['elbHealthCheckScore'] > 0):
        tg_attributes = elbClient.describe_target_group_attributes(
                TargetGroupArn=list(filter(lambda x: x['OutputKey'] == 'TargetGroupArn', event['outputs']))[0]['OutputValue'])
        if list(
                filter(
                    lambda x: x['Key']=='proxy_protocol_v2.enabled',
                    tg_attributes['Attributes']
                )
            )[0]['Value'] == 'false':
            score += 30
            score_data['elbWorkingScore'] = 100

    score_data['totalScore'] = score
    output={
        'totalScore' : score_data['totalScore'],
        'splitScore' : { 'Security Group Fixed' : score_data['securityGroupRuleScore'], 'Health Check Fixed' : score_data['elbHealthCheckScore'], 'ELB Working' : score_data['elbWorkingScore']}
    }
return output