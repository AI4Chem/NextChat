export http_proxy='http://127.0.0.1:7890'
URL='www.youtube.com'

wget -q --proxy-user=test --proxy-password=test --spider $URL
if [ $? = 1 ]
then
    STATUS= echo "Proxy isn't working"

else
  STATUS="Proxy is working."
fi
echo $STATUS