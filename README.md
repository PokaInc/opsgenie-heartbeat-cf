## Deployment

First, package your Cloudformation template:
```bash
aws cloudformation package --template-file opsgenie-heartbeat.yml --s3-bucket {your-bucket-name} --output-template-file out.yml
```

Then, deploy the Cloudformation stack:

```bash
aws cloudformation deploy --template-file out.yml --stack-name {stack_name} --capabilities CAPABILITY_IAM --parameter-overrides OpsGenieHeartbeatApiKey={opsgenie_api_key}
```
