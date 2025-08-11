$(document).ready(function () {
    // Date picker
    $.fn.datepicker.dates['ru'] = {
        days: ["Воскресенье", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"],
        daysShort: ["Вск", "Пнд", "Втр", "Срд", "Чтв", "Птн", "Сбт"],
        daysMin: ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"],
        months: ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
        monthsShort: ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"],
        weekStart: 1
    };
    $('[data-id="datepicker"]').datepicker({
        autoclose: true,
        language: 'ru',
        format: 'dd.mm.yyyy'
    });
    // Date picker

    // Кнопка показать пароль
    $('#showPass').on('click', function(){
        var inputText = $('.pass-value');
        var inputType = inputText.prop('type');
        if (inputType === 'password') {
            inputText.prop('type', 'text');
            $(this).children().removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            inputText.prop('type', 'password');
            $(this).children().removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });
    // Кнопка показать пароль

    // Строка таблицы ссылка
    $('.linkedRow tbody tr').click(function() {
        var url = $(this).data('href');
        if (url) {
            document.location.href = $(this).data('href');
        }
    }).find('a, button, input, select, textarea').hover(function() { // Список тегов при наведении на которые, не будет происходить переход по ссылке
        $(this).parents('tr').unbind('click');
    }, function() {
        $(this).parents('tr').click(function() {
            var url = $(this).data('href');
            if (url) {
                document.location.href = $(this).data('href');
            }
        });
    });
    // Строка таблицы ссылка

});
