document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const mobileMenu = document.getElementById('mobileMenu');
    
    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('active');
        });
    }
    
    // Flash message close button
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(message => {
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '&times;';
        closeBtn.className = 'close-flash';
        closeBtn.addEventListener('click', () => message.remove());
        message.appendChild(closeBtn);
    });
    
    // Path finding form submission
    const pathForm = document.getElementById('pathForm');
    if (pathForm) {
        pathForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const targetUserId = document.getElementById('targetUser').value;
            const pathResult = document.getElementById('pathResult');
            
            if (!targetUserId) return;
            
            pathResult.innerHTML = '<p class="loading">Finding path...</p>';
            
            try {
                const response = await fetch(`/get_path/${targetUserId}`);
                const data = await response.json();
                
                if (data.error) {
                    pathResult.innerHTML = `<p class="error">${data.error}</p>`;
                } else {
                    let pathHTML = '<h4>Shortest Connection Path:</h4><ol class="path-list">';
                    data.path.forEach(user => {
                        pathHTML += `<li>${user.name}</li>`;
                    });
                    pathHTML += '</ol>';
                    pathResult.innerHTML = pathHTML;
                }
            } catch (error) {
                console.error('Error:', error);
                pathResult.innerHTML = '<p class="error">An error occurred while fetching the path.</p>';
            }
        });
    }
    
    // Modal functionality
    const modal = document.getElementById('pathModal');
    if (modal) {
        const closeModal = document.querySelector('.close-modal');
        const modalPathDetails = document.getElementById('modalPathDetails');
        
        if (closeModal) {
            closeModal.addEventListener('click', function() {
                modal.style.display = 'none';
            });
        }
        
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
        
        // Handle path links
        const pathLinks = document.querySelectorAll('.btn-path');
        pathLinks.forEach(link => {
            link.addEventListener('click', async function(e) {
                e.preventDefault();
                const userId = this.getAttribute('data-user-id');
                
                modalPathDetails.innerHTML = '<p class="loading">Finding path...</p>';
                modal.style.display = 'flex';
                
                try {
                    const response = await fetch(this.href);
                    const data = await response.json();
                    
                    if (data.error) {
                        modalPathDetails.innerHTML = `<p class="error">${data.error}</p>`;
                    } else {
                        let pathHTML = '<ol class="path-list">';
                        data.path.forEach(user => {
                            pathHTML += `<li>${user.name}</li>`;
                        });
                        pathHTML += '</ol>';
                        modalPathDetails.innerHTML = pathHTML;
                    }
                } catch (error) {
                    console.error('Error:', error);
                    modalPathDetails.innerHTML = '<p class="error">An error occurred while fetching the path.</p>';
                }
            });
        });
    }
});