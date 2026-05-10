document.addEventListener('DOMContentLoaded', function() {
    const bookSelect = document.getElementById('id_book');
    const memberSelect = document.getElementById('id_member');
    const dueDateInput = document.getElementById('id_due_date');
    
    // Only proceed if elements exist (e.g., on Add Loan page)
    if (!bookSelect || !memberSelect || !dueDateInput) return;

    function fetchAndSetDueDate() {
        const bookId = bookSelect.value;
        const memberId = memberSelect.value;
        
        if (bookId && memberId) {
            // Call our new API
            fetch(`/api/loan_duration/?book_id=${bookId}&member_id=${memberId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.found) {
                        // Calculate due date
                        const today = new Date();
                        const duration = parseInt(data.duration_days);
                        const dueDate = new Date(today);
                        dueDate.setDate(today.getDate() + duration);
                        
                        // Format for Django Date Input (YYYY-MM-DD)
                        const yyyy = dueDate.getFullYear();
                        const mm = String(dueDate.getMonth() + 1).padStart(2, '0');
                        const dd = String(dueDate.getDate()).padStart(2, '0');
                        
                        dueDateInput.value = `${yyyy}-${mm}-${dd}`;
                        
                        // Optionally show a message
                        console.log(`Auto-filled Due Date based on Approved Request: ${duration} days`);
                    }
                })
                .catch(err => console.error('Error fetching loan duration:', err));
        }
    }

    // Add listeners
    bookSelect.addEventListener('change', fetchAndSetDueDate);
    memberSelect.addEventListener('change', fetchAndSetDueDate);
});