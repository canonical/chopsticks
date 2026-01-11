"""Unit tests for SSH utilities."""

from unittest.mock import MagicMock, patch
import socket
import subprocess

from chopsticks.utils.ssh import RemoteExecutor


@patch("chopsticks.utils.ssh.subprocess.run")
@patch("chopsticks.utils.ssh.socket.create_connection")
def test_ssh_connectivity_with_motd(mock_socket, mock_subprocess):
    """Test SSH reachability succeeds with MOTD output."""
    # Mock successful TCP connection
    mock_sock = MagicMock()
    mock_socket.return_value = mock_sock
    
    # Mock SSH command with MOTD output
    motd_output = """Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-91-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com

System information as of Sat Jan 11 12:34:56 UTC 2026

  System load:  0.0               Processes:             123
  Usage of /:   25.0% of 9.78GB   Users logged in:       0

Last login: Sat Jan 11 10:15:22 2026 from 10.0.1.1
reachable
"""
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout=motd_output,
        stderr="",
    )
    
    executor = RemoteExecutor(transport="ssh", user="ubuntu")
    result = executor.test_connectivity("test-host")
    
    assert result.passed is True
    assert "reachable via SSH" in result.message
    assert result.details["ssh_handshake"] == "success"


@patch("chopsticks.utils.ssh.subprocess.run")
@patch("chopsticks.utils.ssh.socket.create_connection")
def test_ssh_connectivity_without_motd(mock_socket, mock_subprocess):
    """Test SSH reachability still works with clean output."""
    mock_sock = MagicMock()
    mock_socket.return_value = mock_sock
    
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout="reachable\n",
        stderr="",
    )
    
    executor = RemoteExecutor(transport="ssh", user="ubuntu")
    result = executor.test_connectivity("test-host")
    
    assert result.passed is True
    assert result.details["ssh_handshake"] == "success"


@patch("chopsticks.utils.ssh.subprocess.run")
@patch("chopsticks.utils.ssh.socket.create_connection")
def test_ssh_connectivity_missing_marker(mock_socket, mock_subprocess):
    """Test SSH reachability fails when marker not in output."""
    mock_sock = MagicMock()
    mock_socket.return_value = mock_sock
    
    # Return MOTD but without the marker
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout="Welcome to Ubuntu 22.04.3 LTS\nLast login: Sat Jan 11 10:15:22 2026\n",
        stderr="",
    )
    
    executor = RemoteExecutor(transport="ssh", user="ubuntu")
    result = executor.test_connectivity("test-host")
    
    assert result.passed is False
    assert result.details["ssh_handshake"] == "failed"
    assert "stdout_sample" in result.details


@patch("chopsticks.utils.ssh.subprocess.run")
@patch("chopsticks.utils.ssh.socket.create_connection")
def test_ssh_connectivity_command_fails(mock_socket, mock_subprocess):
    """Test SSH reachability fails on command error."""
    mock_sock = MagicMock()
    mock_socket.return_value = mock_sock
    
    mock_subprocess.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="Permission denied",
    )
    
    executor = RemoteExecutor(transport="ssh", user="ubuntu")
    result = executor.test_connectivity("test-host")
    
    assert result.passed is False
    assert result.details["ssh_handshake"] == "failed"
    assert "Permission denied" in result.details["error"]


@patch("chopsticks.utils.ssh.socket.create_connection")
def test_ssh_connectivity_tcp_timeout(mock_socket):
    """Test SSH reachability fails on TCP timeout."""
    mock_socket.side_effect = socket.timeout("Connection timed out")
    
    executor = RemoteExecutor(transport="ssh", user="ubuntu")
    result = executor.test_connectivity("test-host")
    
    assert result.passed is False
    assert "timeout" in result.message.lower()


@patch("chopsticks.utils.ssh.socket.create_connection")
def test_ssh_connectivity_connection_refused(mock_socket):
    """Test SSH reachability fails on connection refused."""
    mock_socket.side_effect = ConnectionRefusedError("Connection refused")
    
    executor = RemoteExecutor(transport="ssh", user="ubuntu")
    result = executor.test_connectivity("test-host")
    
    assert result.passed is False
    assert "Connection refused" in result.message
