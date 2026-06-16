param(
    [Parameter(Mandatory=$true)][string]$Title,
    [Parameter(Mandatory=$true)][string]$Message,
    [string]$AppId = "Cowork.StudyReminder"
)

[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] | Out-Null

$EscTitle   = [System.Security.SecurityElement]::Escape($Title)
$EscMessage = [System.Security.SecurityElement]::Escape($Message)

$xmlString = @"
<toast duration="long">
  <visual>
    <binding template="ToastGeneric">
      <text>$EscTitle</text>
      <text>$EscMessage</text>
    </binding>
  </visual>
  <audio src="ms-winsoundevent:Notification.Default" />
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($xmlString)

$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId).Show($toast)
