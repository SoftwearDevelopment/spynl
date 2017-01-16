"""Define functions to send emails."""


import os

from pyramid.renderers import render
from pyramid_mailer import get_mailer
from pyramid_mailer.mailer import DummyMailer
from pyramid_mailer.message import Message

from jinja2 import Environment, Template, TemplateNotFound, FileSystemLoader
import html2text

from spynl.main.utils import (get_logger, get_settings,
                              is_production_environment)
from spynl.main.exceptions import EmailTemplateNotFound
from .locale import TemplateTranslations, SpynlTranslationString


DEFAULT_HTML_TEMPLATE = '''
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
                        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <title>{{subject}}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      </head>
      <body style="margin: 0; padding: 0;">
        <!-- Spynl Default Email Template -->
        <table align="center" cellpadding="0" cellspacing="0" width="400">
        <tr>
          <td align="center" bgcolor="#fff" style="padding: 40px 0 30px 0;"
              style="color: #153643; font-family: Arial, sans-serif;
                     font-size: 16px; line-height: 20px;">
            {{content}}
          </td>
        </tr>
        </table>
      </body>
    </html>'''


def _sendmail(request, recipient, subject, plain_body, html_body=None,
              sender=None, attachments=None, fail_silently=False, mailer=None):
    """
    Send a mail using the pyramid mailer. This function also makes sure
    that if Spynl is not in a production environment, mail is sent to a dummy
    email address.

    :param Request request: the original request
    :param string recipient: addressee
    :param string subject: subject of mail
    :param string plain_body: content of mail
    :param string html_body: html content of mail
    :param string sender: senders address (optional,
                          default: no_reply@<spynl.domain>)
    :param [Attachment] attachments: attachments (optional)
    :param bool fail_silently: keep quiet when connection errors happen
    :param pyramid_mailer.Mailer mailer: mailer object (optional)
    """
    settings = get_settings()
    logger = get_logger()

    if mailer is None:
        mailer = get_mailer(request)

    if not sender:
        sender = settings.get('mail.sender')
        if not sender:
            domain = settings.get('spynl.domain', 'example.com')
            sender = 'no_reply@{}'.format(domain)

    sender = str(sender)
    recipients = None
    # use recipient in unit tests (mailer only writes files) or in real env
    if recipient and (mailer.__class__ is DummyMailer or
                      is_production_environment()):
        recipients = [str(recipient)]
    # otherwise (e.g. during dev) we might use dummy mail address
    elif settings.get('mail.dummy_recipient'):
        recipients = [settings.get('mail.dummy_recipient')]
        logger.info("I will send this email to %s instead of %s.",
                    settings.get('mail.dummy_recipient'), recipient)
    subject = str(subject).rstrip()

    message = Message(sender=sender, recipients=recipients, subject=subject,
                      body=plain_body, html=html_body)
    if attachments:
        for attachment in attachments:
            message.attach(attachment)

    try:
        message.validate()
        logger.info('Sending email titled "%s" to %s from %s',
                    subject, recipients, sender)
        mailer.send_immediately(message, fail_silently=fail_silently)
    except Exception as e:
        logger.exception(e)
        return False

    return True


def send_template_email(request, recipient, template_string=None,
                        template_file=None, plugin=None, replacements={},
                        subject='', fail_silently=False, mailer=None,
                        attachments=None, sender=None):
    """
    Send email using a html template.
    
    The email's content (which can contain HTML code) is defined by a Jinja
    template. This content template can be given either by filename
    <template_file> (absolute path) or directly in string form
    <template_string>. In both cases, the email content gets wrapped by a base
    template which defines a consistent layout. The base template to use is
    defined by a string type setting:
        `base_email_template: absolute path of template
    If the "base template" cannot be loaded the <DEFAULT_HTML_TEMPLATE> is
    used.
    Replacements can be send in to customise the email content.
    If no html or plain text was constructed in the end, replacements are being
    used to construct a basic text to be send as an email.

    In case of a jinja2 template the following assignments are attempted to be
    loaded from the template:
        `default_subject`: will be used if no subject was passed
    """
    if (template_string is None and template_file is None) or \
            (template_string is not None and template_file is not None):
        raise Exception('One of <template_string> or <template_file> must be '
                        'given.')
    text_body = ''
    if subject:
        replacements['subject'] = subject
    for key, value in replacements.items():
        if isinstance(value, SpynlTranslationString):
            replacements[key] = value.translate()

    if template_file is not None:
        try:
            replacements['content'] = render(template_file, replacements,
                                             request=request)
        except TemplateNotFound:
            raise EmailTemplateNotFound(template_file)

        if not subject:  # update with possible subject defined in template
            subject = value_from_template(template_file, 'default_subject',
                                          request, replacements, plugin)
            replacements.update(subject=subject)
    else:
        replacements['content'] = Template(template_string).render(
            **replacements)

    # Render the base template with the content of the given template
    base_template = get_settings().get('base_email_template')
    if base_template is not None:
        html_body = render(base_template, replacements, request=request)
    else:
        html_body = Template(DEFAULT_HTML_TEMPLATE).render(**replacements)
    html_body = html_body.replace('\n', '')

    text_maker = html2text.HTML2Text()
    text_maker.ignore_images = True
    text_body = text_maker.handle(html_body)

    if not text_body and not html_body:
        str_replacements = '\n'.join(['{}: {}'.format(key, value)
                                      for key, value in replacements.items()])
        text_body = 'Your account has been changed.\n' + str_replacements
        template = Template(DEFAULT_HTML_TEMPLATE)
        replacements.update(subject=subject, content=text_body)
        html_body = template.render(**replacements)
        get_logger(__name__).error(
            'Body was not found in body_string or email template: %s',
            template)

    return _sendmail(request, recipient, subject, text_body, html_body,
                     fail_silently=fail_silently, mailer=mailer,
                     attachments=attachments, sender=sender)


def value_from_template(template_file, var, request, replacements,
                        plugin=None):
    """
    Return the value of given <var> defined inside the <template_file>.

    Set the static_url filter for templates to construct urls for static files.
    If plugin was given, install plugin's translations to the environment. 
    """
    path, filename = os.path.split(template_file)
    env = Environment(loader=FileSystemLoader(path),
                      extensions=['jinja2.ext.i18n'])
    env.filters['static_url'] = request.static_url
    if plugin is not None:
        translations = TemplateTranslations(plugin)
        env.install_gettext_translations(translations)

    template = env.get_template(filename)
    template_module = template.make_module(vars=replacements)
    return getattr(template_module, var, '')
