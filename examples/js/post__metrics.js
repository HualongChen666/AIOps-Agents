// 示例：POST /metrics
fetch('http://localhost:8080/api/v1/metrics', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
