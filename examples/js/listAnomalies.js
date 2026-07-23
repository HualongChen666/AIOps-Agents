// 示例：List anomalies
fetch('http://localhost:8080/api/v1/anomalies', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
