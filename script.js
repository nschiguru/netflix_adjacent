// REPLACE THIS URL with your API Gateway URL!
const API_URL = 'https://az4y9bink2.execute-api.us-east-1.amazonaws.com/prod/content';

let currentUser = null;
let currentUserId = null;
let currentMovieId = null;
let isAuthenticated = false;

async function login() {
    console.log('Login function called'); // Debug
    
    const usernameInput = document.getElementById('username');
    const accessKeyInput = document.getElementById('accessKey');
    
    console.log('Username input:', usernameInput); // Debug
    console.log('AccessKey input:', accessKeyInput); // Debug
    
    if (!usernameInput || !accessKeyInput) {
        alert('Error: Cannot find input fields');
        return;
    }
    
    const username = usernameInput.value;
    const accessKey = accessKeyInput.value;
    
    console.log('Username:', username); // Debug
    console.log('AccessKey:', accessKey); // Debug
    
    if (!username || !accessKey) {
        alert('Please enter both IAM Username and Access Key');
        return;
    }
    
    // Show loading state
    const loginBtn = document.querySelector('.login-section button');
    const originalText = loginBtn.textContent;
    loginBtn.textContent = 'Authenticating...';
    loginBtn.disabled = true;
    
    try {
        console.log('Sending request to:', API_URL); // Debug
        
        // Call Lambda function to authenticate user
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'authenticate',
                username: username,
                accessKey: accessKey
            })
        });
        
        console.log('Response status:', response.status); // Debug
        
        const result = await response.json();
        console.log('Result:', result); // Debug
        
        const data = result.body ? JSON.parse(result.body) : result;
        console.log('Parsed data:', data); // Debug
        
        if (data.authenticated) {
            // Authentication successful
            isAuthenticated = true;
            currentUser = data.username;
            currentUserId = data.userId;
            
            document.getElementById('userDisplay').textContent = currentUser;
            document.getElementById('loginSection').style.display = 'none';
            document.getElementById('moviesSection').style.display = 'block';
            
            loadAllProgress();
        } else {
            // Authentication failed
            alert('Authentication Failed: ' + (data.error || 'Invalid credentials or insufficient privileges'));
            loginBtn.textContent = originalText;
            loginBtn.disabled = false;
        }
    } catch (error) {
        alert('Authentication Error: ' + error.message);
        console.error('Authentication error:', error);
        loginBtn.textContent = originalText;
        loginBtn.disabled = false;
    }
}

// Rest of your existing code...
async function loadAllProgress() {
    if (!isAuthenticated) {
        alert('Please login first');
        return;
    }
    
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
                    userId: currentUserId,
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
    if (!isAuthenticated) {
        alert('Please login first');
        return;
    }
    
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

async function backToMovies() {
    const videoPlayer = document.getElementById('videoPlayer');

    // Prevent saving if no movie is currently playing
    if (!currentMovieId || !currentUserId || !videoPlayer.duration) {
        document.getElementById('playerSection').style.display = 'none';
        document.getElementById('moviesSection').style.display = 'block';
        videoPlayer.pause();
        videoPlayer.src = '';
        return;
    }

    const progress = (videoPlayer.currentTime / videoPlayer.duration) * 100;
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'saveProgress',
                userId: currentUserId,
                movieId: currentMovieId,
                progress: progress,
                timestamp: new Date().toISOString()
            })
        });
        
        if(!response.ok) {
            throw new Error('Network response was not ok');
        }

        alert('Progress saved successfully!');
    } catch (error) {
        alert('Error saving progress: ' + error.message);
        console.error('Error saving the progress: ' + error);
    }

    document.getElementById('playerSection').style.display = 'none';
    document.getElementById('moviesSection').style.display = 'block';
    
    videoPlayer.pause();
    videoPlayer.src = '';
    
    loadAllProgress();
}

async function saveProgress() {
    if (!isAuthenticated) {
        alert('Please login first');
        return;
    }
    
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
                userId: currentUserId,
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