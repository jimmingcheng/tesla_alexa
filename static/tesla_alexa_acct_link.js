$(document).ready(function() {
    var url = new URL(window.location);
    var redirect_uri = url.searchParams.get('redirect_uri');
    var state = url.searchParams.get('state');

    $('#login').submit(function(event) {
        var email = $('input[name=email]').val();
        var password = $('input[name=password]').val();
        $.post(
            AUTH_URL,  // set this in tesla_alexa_acct_link_settings.js
            JSON.stringify({
                'email': email,
                'password': password,
            }),
            function(data) {
                if (data.alexa_access_token) {
                    window.location = redirect_uri +
                        '#state=' + state + '&token_type=Bearer' + 
                        '&access_token=' + data.alexa_access_token;
                }
                else {
                    $('#alert').text('Unable to log in. Try again.');
                }
            },
            'json'
        );
    });
});
