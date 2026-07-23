// 示例：POST /submit
fetch('http://localhost:8080/api/v1/submit', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
