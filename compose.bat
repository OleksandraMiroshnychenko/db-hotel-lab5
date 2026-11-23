docker-compose -p lab5 stop
docker-compose -p lab5 down --volumes
docker-compose -p lab5 up -d --build
echo Waiting for the database to start...
timeout /t 30 /nobreak
docker exec lab5-app-1 python -m hotel.seed