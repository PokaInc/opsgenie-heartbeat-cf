# opsgenie-heartbeat-cf

Example of CloudFormation Custom Resource for managing OpsGenie Heartbeats

As seen on [Managing OpsGenie Heartbeats using CloudFormation](https://medium.com/poka-techblog/managing-opsgenie-heartbeats-using-cloudformation-f7a328a75eea)


## Deployment

First, package your Cloudformation template:
```bash
aws cloudformation package --template-file opsgenie-heartbeat.yml --s3-bucket {your-bucket-name} --output-template-file out.yml
```

Then, deploy the Cloudformation stack:

```bash
aws cloudformation deploy --template-file out.yml --stack-name {stack_name} --capabilities CAPABILITY_IAM --parameter-overrides OpsGenieHeartbeatApiKey={opsgenie_api_key}
```
