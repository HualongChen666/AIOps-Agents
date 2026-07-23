// 示例：POST /intelligence/route-alerts
fetch('http://localhost:8080/api/v1/intelligence/route-alerts', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
