import boto3
import time
import json
import os


def handler(event, context):
    s3_client = boto3.client('s3')
    #print(event)
    #print(context)
    for i in range(len(event['outputs'])) :
        if event['outputs'][i]['OutputKey'] == "InstanceId" :
            instance_id=event['outputs'][i]['OutputValue']

    score_script_s3_bucket=os.environ['CHALLENGE_RESOURCE_BUCKET']
    path = "input/" + event['ChallengeId'] + ".sh"
    #print(path);
    score_script_s3_key=path

    #score_script_s3_bucket="excelfilebucket"
    #score_script_s3_key="bottlenose-route.sh"

    score_script=s3_client.get_object(
                        Bucket=score_script_s3_bucket,
                        Key=score_script_s3_key,
                    )["Body"].read().decode('utf-8')

    data={"instance_id": instance_id, "score_script": score_script}

    return ssmscore(data)


def ssmscore(data):

    ssm_client = boto3.client('ssm')
    s3_client = boto3.client('s3')

    instance= data["instance_id"]
    score_script= data["score_script"]
    ssm_output_bucket_name= os.environ['CHALLENGE_RESOURCE_BUCKET']
    #ssm_output_bucket_name="excelfilebucket"
    score= 0
    ssm_command = ssm_client.send_command( 
        InstanceIds=[instance],
        DocumentName='AWS-RunShellScript', 
        Comment='run dummy file', 
        Parameters={ "commands":[score_script] },
        OutputS3BucketName=ssm_output_bucket_name,
        OutputS3KeyPrefix="output/" + instance
    )
    #print('SSM command ID:'+ ssm_command["Command"]["CommandId"])
    check_ssm_success= ''
    check_time=50
    while check_time>0:
        time.sleep(1)
        check_time-=1
        check_ssm_success = ssm_client.list_commands(
            CommandId=ssm_command['Command']['CommandId'],
            InstanceId= instance,
            Filters=[
                {
                    'key': 'Status',
                    'value': 'Success'
                },
            ]
        )
        if check_ssm_success['Commands'] != []:
            break
        if check_time == 0:
            check_ssm_success= 'error'
            
    if check_ssm_success != 'error':
        #print('Getting command output')
        command_output_key = "output/" + instance + "/" + ssm_command["Command"]["CommandId"] + "/" + instance + "/awsrunShellScript/0.awsrunShellScript/stdout"

        #print('Output S3: '+ command_output_key)
        command_output = s3_client.get_object(
                    Bucket=ssm_output_bucket_name,
                    Key=command_output_key,
                )["Body"].read()
        #print(command_output)
        
    else:
        #print('Check timeout')
        return -1

    return cal_score(command_output)


def cal_score(command_output):

    score_data = {}
    score_data['totalScore'] = 0
    score_data['routeTableScore'] = 0
    score_data['ipTableScore'] = 0
    score_data['curlScore'] = 0

    outputOfCommand=command_output.decode('utf-8').split(":")[0]
    routeTable=command_output.decode('utf-8').split(":")[1]
    ipTable=command_output.decode('utf-8').split(":")[2]
    curl=command_output.decode('utf-8').split(":")[3].rstrip()

    if routeTable == "true":
        score_data['routeTableScore'] = 100
    if ipTable == "true":
        score_data['ipTableScore'] = 100
    if curl == "true":
        score_data['curlScore'] = 100

    #add based on conditions
    if command_output.decode('utf-8').find('Sorry! You have not completed the lab. Please follow the steps mentioned in wiki to finish the lab') != -1:
        score_data['totalScore'] = 0
    if command_output.decode('utf-8').find('You have completed 33 percent of the Lab correctly') != -1:
        score_data['totalScore'] = 33
    if command_output.decode('utf-8').find('You have completed 66 percent of the Lab correctly') != -1:
        score_data['totalScore'] = 66
    if command_output.decode('utf-8').find('You have completed the lab successfully') != -1:
        score_data['totalScore'] = 100
    
    output={
        'totalScore' : score_data['totalScore'],
        'splitScore' : { 'Route Table' : score_data['routeTableScore'], 'Iptable' : score_data['ipTableScore'], 'Website Running' : score_data['curlScore']}
    }
    #print(score_data['ipTableScore'])
    return output