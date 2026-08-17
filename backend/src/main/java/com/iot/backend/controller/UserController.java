package com.iot.backend.controller;

import com.iot.backend.entity.User;
import com.iot.backend.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/user")
@CrossOrigin(origins = "*")
public class UserController {

    @Autowired
    private UserRepository userRepository;

    // Lấy thông tin user hiện tại (Mặc định lấy user admin)
    @GetMapping("/profile")
    public ResponseEntity<User> getProfile() {
        return userRepository.findByUsername("admin")
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}