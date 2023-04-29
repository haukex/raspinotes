#!/usr/bin/perl
use warnings;
use strict;
# should run on vanilla Perl, use core modules only
use Sys::Hostname 'hostname';
use Digest::SHA 'hmac_sha256_base64';

my $SECRET = 'password';  # for signature, so server can verify authenticity
my $BASEURL = 'https://example.com/hellorpi/'; # end with slash!

# IPv4 only at the moment:
my @ips = grep { /\A\d+(?:\.\d+){3}\z/ } split ' ', `/usr/bin/hostname -I`;
die "hostname: \$?=$?" if $?;
exit unless @ips;

my $host = hostname;
die $host unless $host=~/\A[A-Za-z0-9\.\-\_]+\z/;

my $url = join '/', $host, @ips;

my $sig = hmac_sha256_base64($url, $SECRET);
$sig =~ tr#+/#-_#;  # like Python's base64.urlsafe_b64encode
#$sig =~ s/=+$//g;  # not actually needed, docs say there won't be padding

my @cmd = ('curl','--silent','--max-time','5',
	'--fail','--fail-early','--show-error',
	'--header','Content-Type: application/octet-stream',
	'--data-raw',$sig,"$BASEURL$url",'--output','/dev/null');
system(@cmd) and die "curl: \$?=$?, \$!=$!";
