$(window).on('pytsite.form.ready', function (e, form) {
    $(form).on('pytsite.form.forward', function () {
        form.em.find('.widget-uid-description input').focus(function () {
            var descriptionInput = $(this);
            var titleInput = form.em.find('.widget-uid-title input');

            if (descriptionInput.val() == '')
                descriptionInput.val(titleInput.val());
        });
    });
});
