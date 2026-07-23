// 示例：GET /conversation/{conversation_id}
fetch('http://localhost:8080/api/v1/conversation/{conversation_id}', {
    method: 'GET'
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
