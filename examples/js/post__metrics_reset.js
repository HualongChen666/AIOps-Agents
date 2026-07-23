// 示例：POST /metrics/reset
fetch('http://localhost:8080/api/v1/metrics/reset', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
