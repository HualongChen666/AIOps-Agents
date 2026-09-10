
const authToken = process.env.AIOPS_TOKEN || 'YOUR_TOKEN';
// 示例：POST /database
fetch(`http://localhost:8000/api/v1/database`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${authToken}` }
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
