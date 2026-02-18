#/bin/bash

uvicorn main:create_app --app-dir src --host 0.0.0.0 --port 8080 --no-access-log --factory