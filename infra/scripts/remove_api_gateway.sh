aws apigatewayv2 get-domain-names --region eu-central-1
# For each of these (majidkhoshrou.com / www.majidkhoshrou.com):
aws apigatewayv2 get-api-mappings --region eu-central-1 --domain-name majidkhoshrou.com
# (if any mappings, delete them)
aws apigatewayv2 delete-api-mapping --region eu-central-1 --domain-name majidkhoshrou.com --api-mapping-id <ID>
# then delete the domain
aws apigatewayv2 delete-domain-name --region eu-central-1 --domain-name majidkhoshrou.com
# repeat for www
aws apigatewayv2 delete-domain-name --region eu-central-1 --domain-name www.majidkhoshrou.com
