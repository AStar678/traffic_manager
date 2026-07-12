package com.visiondrive.security;

public record AuthenticatedUser(Long id, String username, String role) {
}
