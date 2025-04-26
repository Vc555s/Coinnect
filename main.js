// Fetch popular skills for the homepage
document.addEventListener('DOMContentLoaded', function() {
    // Only run on homepage if the popular skills list exists
    const popularSkillsList = document.getElementById('popular-skills-list');
    if (popularSkillsList) {
        fetchPopularSkills();
    }
});

function fetchPopularSkills() {
    fetch('/dashboard')
        .then(response => response.json())
        .then(data => {
            const popularSkillsList = document.getElementById('popular-skills-list');
            popularSkillsList.innerHTML = '';
            
            if (data.popular_skills && data.popular_skills.length > 0) {
                data.popular_skills.forEach(skill => {
                    const listItem = document.createElement('li');
                    listItem.textContent = `${skill.name} (offered by ${skill.count} users)`;
                    popularSkillsList.appendChild(listItem);
                });
            } else {
                const listItem = document.createElement('li');
                listItem.textContent = 'No skills available yet.';
                popularSkillsList.appendChild(listItem);
            }
        })
        .catch(error => {
            console.error('Error fetching popular skills:', error);
            const popularSkillsList = document.getElementById('popular-skills-list');
            popularSkillsList.innerHTML = '<li>Error loading skills. Please try again later.</li>';
        });
}