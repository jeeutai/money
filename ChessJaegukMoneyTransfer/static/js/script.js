// DOM이 로드된 후 실행
document.addEventListener('DOMContentLoaded', function() {
    // 알림 메시지 자동 닫기
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.style.display = 'none';
            }, 500);
        }, 3000);
    });

    // QR 코드 스캔 (실제 구현 시에는 라이브러리 사용)
    const qrForm = document.getElementById('qr-form');
    if (qrForm) {
        qrForm.addEventListener('submit', function(e) {
            // QR 코드 스캔 기능을 여기에 구현
            // 여기서는 단순 폼 제출로 처리
        });
    }
});

// 금액 입력 시 숫자만 입력되도록 처리
const amountInputs = document.querySelectorAll('input[type="number"]');
amountInputs.forEach(function(input) {
    input.addEventListener('input', function() {
        this.value = this.value.replace(/[^0-9]/g, '');
    });
});