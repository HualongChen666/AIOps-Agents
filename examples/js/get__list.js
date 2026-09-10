
const authToken = process.env.AIOPS_TOKEN || 'YOUR_TOKEN';
// 示例：GET /list
fetch(`http://localhost:8000/api/v1/list`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${authToken}` }
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
