```
oc apply -f configmap.yaml
oc process -f rabbitmq.yaml | oc apply -f -
oc process -f redis.yaml | oc apply -f -
oc process -f telemetry-receiver.yaml | oc apply -f -
oc process -f consumer.yaml | oc apply -f -
``` 