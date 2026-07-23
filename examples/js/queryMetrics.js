// 示例：Query metrics
fetch('http://localhost:8080/api/v1/metrics', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
