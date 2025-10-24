// REPLACE THIS URL with your API Gateway URL!
const API_URL = 'https://az4y9bink2.execute-api.us-east-1.amazonaws.com/prod/content';

let currentUser = null;
let currentMovieId = null;

async function login() {
    const userId = document.getElementById('userId').value;
    
    if (!userId) {
        alert('Please enter a User ID');
        return;
    }
    
    currentUser = userId;
    document.getElementById('userDisplay').textContent = currentUser;
    document.getElementById('loginSection').style.display = 'none';
    document.getElementById('moviesSection').style.display = 'block';
    
    loadAllProgress();
}

async function loadAllProgress() {
    const movies = ['movie1', 'movie2', 'movie3'];
    
    for (const movieId of movies) {
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: 'getProgress',
                    userId: currentUser,
                    movieId: movieId
                })
            });
            
            const result = await response.json();
            const data = result.body ? JSON.parse(result.body) : result;
            const progress = data.watchProgress || 0;
            document.getElementById(`progress-${movieId}`).style.width = progress + '%';
        } catch (error) {
            console.error(`Error loading progress for ${movieId}:`, error);
        }
    }
}

async function playMovie(movieId) {
    currentMovieId = movieId;
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'getVideo',
                movieId: movieId
            })
        });
        
        const result = await response.json();
        const data = result.body ? JSON.parse(result.body) : result;
        
        if (data.videoUrl) {
            document.getElementById('moviesSection').style.display = 'none';
            document.getElementById('playerSection').style.display = 'block';
            document.getElementById('currentMovie').textContent = `Now Playing: ${movieId}`;
            
            const videoPlayer = document.getElementById('videoPlayer');
            videoPlayer.src = data.videoUrl;
            videoPlayer.play();
        }
    } catch (error) {
        alert('Error loading video: ' + error.message);
        console.error(error);
    }
}

function backToMovies() {
    document.getElementById('playerSection').style.display = 'none';
    document.getElementById('moviesSection').style.display = 'block';
    
    const videoPlayer = document.getElementById('videoPlayer');
    videoPlayer.pause();
    videoPlayer.src = '';
    
    loadAllProgress();
}

async function saveProgress() {
    const videoPlayer = document.getElementById('videoPlayer');
    const progress = (videoPlayer.currentTime / videoPlayer.duration) * 100;
    
    try {
        await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'saveProgress',
                userId: currentUser,
                movieId: currentMovieId,
                progress: progress,
                timestamp: new Date().toISOString()
            })
        });
        
        alert('Progress saved successfully!');
    } catch (error) {
        alert('Error saving progress: ' + error.message);
        console.error(error);
    }
}