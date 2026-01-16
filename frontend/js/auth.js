/**
 * FluentAI Authentication Module
 */

import { api } from './api.js';
import { toast, loading } from './app.js';

// Login Handler
export async function handleLogin(event) {
    event.preventDefault();
    
    const form = event.target;
    const email = form.querySelector('#email').value;
    const password = form.querySelector('#password').value;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Validation
    if (!email || !password) {
        toast.error('Please fill in all fields');
        return;
    }
    
    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading-spinner" style="width:20px;height:20px;"></span> Logging in...';
        
        const data = await api.login(email, password);
        toast.success('Welcome back!');
        
        // Check if user needs assessment
        if (!data.user.cefr_level) {
            window.location.href = 'placement-test.html';
        } else {
            window.location.href = 'dashboard.html';
        }
    } catch (error) {
        toast.error(error.message || 'Login failed. Please check your credentials.');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Log In';
    }
}

// Register Handler
export async function handleRegister(event) {
    event.preventDefault();
    
    const form = event.target;
    const name = form.querySelector('#name').value;
    const email = form.querySelector('#email').value;
    const password = form.querySelector('#password').value;
    const confirmPassword = form.querySelector('#confirm-password')?.value;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Validation
    if (!name || !email || !password) {
        toast.error('Please fill in all fields');
        return;
    }
    
    if (confirmPassword && password !== confirmPassword) {
        toast.error('Passwords do not match');
        return;
    }
    
    if (password.length < 6) {
        toast.error('Password must be at least 6 characters');
        return;
    }
    
    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading-spinner" style="width:20px;height:20px;"></span> Creating account...';
        
        await api.register(email, password, name);
        toast.success('Account created successfully!');
        
        // Redirect to placement test
        window.location.href = 'placement-test.html';
    } catch (error) {
        toast.error(error.message || 'Registration failed. Please try again.');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Account';
    }
}

// Logout Handler
export function handleLogout() {
    api.logout();
}

// Initialize Auth Forms
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    // Check if already logged in
    if (api.isAuthenticated()) {
        const isAuthPage = window.location.pathname.includes('login') || 
                          window.location.pathname.includes('register');
        if (isAuthPage) {
            // Could redirect to dashboard
        }
    }
});
