const conversationId = 'YOUR_CONVERSATION_ID';
const authToken = process.env.AIOPS_TOKEN || 'YOUR_TOKEN';
// 示例：GET /conversation/{conversation_id}
fetch(`http://localhost:8000/api/v1/conversation/${conversationId}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${authToken}` }
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error('Request error:', err));
