// 示例：POST /learning/update
fetch('http://localhost:8080/api/v1/learning/update', {
    method: 'POST'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
