include .aws_service_settings


venv: requirements.txt
	rm -rf venv
	virtualenv -p python3.6 venv
	venv/bin/pip install -r requirements.txt --extra-index-url https://test.pypi.org/simple

.PHONY: test
test: venv
	venv/bin/pytest tests

.PHONY: package
package: venv
	rm -rf build/
	mkdir build/
	cp -r venv/lib/python3.6/site-packages/* build/
	cp -r tesla_alexa/ build/
	cp -r lambda_functions/ build/
	cd build;zip -r deploy.zip .

.PHONY: deploy-static
deploy-static:
	aws s3 sync static/ s3://$(STATIC_S3_BUCKET)/ \
	--exclude '*' \
	--include '*.css' \
	--include '*.html' \
	--include '*.js'

.PHONY: deploy
deploy: package deploy-static
	aws lambda update-function-code \
	--region $(TESLA_ALEXA_REGION) \
	--function-name $(TESLA_ALEXA_FUNC_NAME) --zip-file 'fileb://build/deploy.zip'
	aws lambda update-function-code \
	--region $(TESLA_ALEXA_ACCT_LINK_REGION) \
	--function-name $(TESLA_ALEXA_ACCT_LINK_FUNC_NAME) --zip-file 'fileb://build/deploy.zip'

.PHONY: clean
clean:
	rm -rf venv
	rm -f deploy.zip
