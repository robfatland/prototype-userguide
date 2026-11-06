# Deploying the public demo (AWS, securecomputing account, us-west-2)

One-time setup. All resources live in account **securecomputing** (084375582624), region
**us-west-2**. The only unbounded cost is Bedrock tokens, gated by the $10/day cap in the ask
Lambda. Everything else is free-tier / pennies.

Prereqs: AWS CLI configured for the `securecomputing` profile; `python`/`boto3` locally for
`admin.py`. Set `export AWS_PROFILE=securecomputing AWS_DEFAULT_REGION=us-west-2`.

## 1. Verify the alert email in SES (sandbox mode)
SES starts in sandbox and can only send to verified addresses — fine, we only email the operator.
```
aws ses verify-email-identity --email-address rob5@uw.edu
```
Click the link SES emails to rob5@uw.edu. (No need to leave sandbox.)

## 2. DynamoDB state table
```
aws dynamodb create-table --table-name ooi-ug-state \
  --attribute-definitions AttributeName=k,AttributeType=S \
  --key-schema AttributeName=k,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

## 3. IAM role for the Lambdas
Create a role `ooi-ug-lambda` trusted by lambda.amazonaws.com with an inline policy allowing:
`bedrock:InvokeModel` on the Sonnet inference profile + underlying models;
`dynamodb:GetItem/PutItem/UpdateItem/Scan` on the `ooi-ug-state` table;
`ses:SendEmail`; and the basic Lambda logging actions (`logs:CreateLogGroup/CreateLogStream/PutLogEvents`).
(Policy JSON stub: see `iam-policy.json` once you decide exact ARNs.)

## 4. Package & create the two Lambdas
Both share `state.py`. Zip the handler + state.py together.
```
cd public
zip ask.zip ask_lambda.py state.py
zip burn.zip burn_lambda.py state.py

aws lambda create-function --function-name ooi-ug-ask \
  --runtime python3.12 --handler ask_lambda.handler --timeout 60 --memory-size 256 \
  --role arn:aws:iam::084375582624:role/ooi-ug-lambda --zip-file fileb://ask.zip \
  --environment "Variables={OOI_UG_MODEL_ID=us.anthropic.claude-sonnet-4-6,DAILY_CAP_USD=10,ALERT_EMAIL=rob5@uw.edu,PRICE_IN_PER_MTOK=3.30,PRICE_OUT_PER_MTOK=16.50,OOI_UG_BASE_URL=https://robfatland.github.io/prototype-userguide/}"

aws lambda create-function --function-name ooi-ug-burn \
  --runtime python3.12 --handler burn_lambda.handler --timeout 30 --memory-size 128 \
  --role arn:aws:iam::084375582624:role/ooi-ug-lambda --zip-file fileb://burn.zip \
  --environment "Variables={DAILY_CAP_USD=10,ALERT_EMAIL=rob5@uw.edu,OOI_UG_LAUNCH_DATE=$(date +%F)}"
```
`boto3` is in the Lambda runtime already; no extra dependency layer needed.

## 5. HTTPS endpoint for the ask Lambda — use API Gateway, NOT a Function URL

**Important (learned the hard way):** the `securecomputing` account is in the UW eScience AWS
Organization, and an org SCP **denies `lambda:InvokeFunctionUrl`**. A public (`AuthType NONE`)
Function URL returns 403 AccessDenied, and fronting it with CloudFront + OAC does *not* help —
the SCP denies the action for the CloudFront service principal too. Use an **API Gateway HTTP API
with a Lambda proxy integration** instead; that uses `lambda:InvokeFunction`, which the SCP allows.

```
# HTTP API with proxy integration (payload format 2.0 — matches the handler's event shape) + CORS.
API_ID=$(aws apigatewayv2 create-api --name ooi-ug-http --protocol-type HTTP \
  --target arn:aws:lambda:us-west-2:084375582624:function:ooi-ug-ask \
  --cors-configuration AllowOrigins='*',AllowMethods='POST,OPTIONS',AllowHeaders='content-type' \
  --query ApiId --output text)

# allow API Gateway to invoke the Lambda
aws lambda add-permission --function-name ooi-ug-ask --statement-id apigw-invoke \
  --action lambda:InvokeFunction --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-west-2:084375582624:$API_ID/*/*"

# the endpoint:
aws apigatewayv2 get-api --api-id "$API_ID" --query ApiEndpoint --output text
```
`create-api --target` auto-creates the integration, the `$default` route, and an auto-deploy
`$default` stage. Copy the ApiEndpoint into `docs/ask.html` (`const ENDPOINT = ...`), commit, and
push so GitHub Pages serves it. The handler reads `event.requestContext.http.method` and
`event.body`, which is exactly the HTTP API payload-format-2.0 shape — no handler change needed.

Current live endpoint: `https://q1uauf9sq2.execute-api.us-west-2.amazonaws.com/` (API id `q1uauf9sq2`).

## 6. Daily burn schedule (~00:05 UTC)
```
aws scheduler create-schedule --name ooi-ug-burn-daily \
  --schedule-expression "cron(5 0 * * ? *)" \
  --flexible-time-window "Mode=OFF" \
  --target "Arn=arn:aws:lambda:us-west-2:084375582624:function:ooi-ug-burn,RoleArn=arn:aws:iam::084375582624:role/ooi-ug-scheduler"
```
(The scheduler needs a small role allowed to invoke ooi-ug-burn, or use EventBridge Rules.)

## 7. Account-level backstop
```
# AWS Budgets: a monthly alert at a number you choose, as a second net under the daily cap.
```

## 8. Mint the first token and send the link
```
export OOI_UG_SITE_URL=https://robfatland.github.io/prototype-userguide/ask.html
python admin.py redo        # prints the link with ?token=... — paste into the email to 10 people
python admin.py status      # sanity check
```

## Operating
- `python admin.py status`   — spend today, token, frozen state
- `python admin.py freeze`   — hard-off (returns "offline", no Bedrock)
- `python admin.py unfreeze` — back on
- `python admin.py redo`     — kill a leaked/abused token, mint + print a new link
- `python admin.py burn`     — send the daily email now (test)

## Teardown
Delete the two Lambdas, the API Gateway HTTP API (`aws apigatewayv2 delete-api --api-id q1uauf9sq2`),
the EventBridge daily rule, and the DynamoDB table. Nothing else persists cost.

The ask Lambda still has an (unreachable, AWS_IAM) Function URL left over from the first attempt;
it is harmless and can be deleted with `aws lambda delete-function-url-config --function-name ooi-ug-ask`.
