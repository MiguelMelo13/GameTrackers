document.addEventListener('DOMContentLoaded', function () {
    // Update <select> color based on the selected option
    document.querySelectorAll('select[name="status"]').forEach(select => {
        const selected = select.options[select.selectedIndex];
        if (selected) select.style.color = selected.style.color;

        select.addEventListener('change', function () {
            this.style.color = this.options[this.selectedIndex].style.color;
            this.form.submit();
        });
    });

    // Modal feedback handling
    const modalElement = document.getElementById('feedbackModal');
    if (modalElement && modalElement.querySelector('.alert')) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();

        modalElement.addEventListener('hidden.bs.modal', () => {
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) backdrop.remove();
            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
        });
    }

    // Trigger delete modal
    document.querySelectorAll('.trigger-delete-modal').forEach(button => {
        button.addEventListener('click', () => {
            const form = document.getElementById('confirmDeleteForm');
            form.action = button.dataset.formAction;
            const modal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
            modal.show();
        });
    });
});
